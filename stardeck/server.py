"""StarDeck server application."""

import asyncio
import json
import secrets
import time
from contextlib import asynccontextmanager
from pathlib import Path

from star_drawing import DrawingCanvas
from starhtml import (
    Button,
    Div,
    Relay,
    ScriptEvent,
    Signal,
    Span,
    elements,
    execute_script,
    format_event,
    get,
    signals,
    sse,
    star_app,
)
from starhtml.datastar import evt, js, seq
from starhtml.plugins import motion, resize
from starhtml.realtime import SSE_HEADERS
from starlette.responses import JSONResponse, StreamingResponse

from stardeck.models import DrawingStore
from stardeck.parser import build_click_signals, deck_has_clicks, parse_deck
from stardeck.presenter import create_presenter_view
from stardeck.renderer import (
    HASH_UPDATE_EFFECT,
    SLIDE_HEIGHT,
    SLIDE_WIDTH,
    VIEWBOX_HEIGHT,
    VIEWBOX_WIDTH,
    build_grid_cards,
    build_grid_modal,
    render_slide,
)
from stardeck.themes import deck_hdrs

_AUDIENCE_CANVAS = "#audience-canvas"
_SSE_TIMEOUT = 30.0


async def _sse_stream(relay, initial_events=None):
    queue = relay.subscribe()
    try:
        if initial_events:
            for event in initial_events:
                yield format_event(event)
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=_SSE_TIMEOUT)
                yield format_event(event)
            except TimeoutError:
                yield ": keepalive\n\n"
    except asyncio.CancelledError:
        pass
    finally:
        relay.unsubscribe(queue)


class FileWatcher:
    def __init__(self, path: Path, on_change):
        self.path = path.resolve()
        self.on_change = on_change
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        from watchfiles import awatch

        self._stop_event.clear()
        async for changes in awatch(self.path, stop_event=self._stop_event):
            if any(Path(p) == self.path for _, p in changes):
                self.on_change()

    def stop(self) -> None:
        self._stop_event.set()


def _drawing_script(selector: str, data_json: str, *, clear: bool = False) -> str:
    clear_call = "c.clear();" if clear else ""
    return (
        f"(()=>{{const c=document.querySelector('{selector}');"
        f"if(!c||!c.applyRemoteChanges)return;"
        f"{clear_call}c.applyRemoteChanges({data_json})}})()"
    )


class PresentationState:
    def __init__(self, deck):
        self.deck = deck
        self.slide_index = 0
        self.clicks = 0
        self.relay = Relay()
        self.drawing = DrawingStore()

    @property
    def current_slide(self):
        return self.deck.slides[self.slide_index]

    @property
    def next_slide(self):
        if self.slide_index + 1 < self.deck.total:
            return self.deck.slides[self.slide_index + 1]
        return None

    @property
    def max_clicks(self):
        return self.current_slide.max_clicks

    def broadcast(self):
        self.relay.emit_signals(
            {
                "slide_index": self.slide_index,
                "clicks": self.clicks,
                "max_clicks": self.max_clicks,
            }
        )
        self.relay.emit_element(render_slide(self.current_slide, self.deck), "#slide-content")
        snapshot = self.drawing.get_snapshot(self.slide_index)
        snapshot_json = json.dumps(snapshot) if snapshot else "[]"
        self.relay.emit_script(_drawing_script(_AUDIENCE_CANVAS, snapshot_json, clear=True))

    def goto_slide(self, idx: int, clicks: int = 0):
        idx = max(0, min(idx, self.deck.total - 1))
        slide = self.deck.slides[idx]
        clicks = max(0, min(clicks, slide.max_clicks))
        self.slide_index = idx
        self.clicks = clicks
        self.broadcast()

    def next(self):
        if self.clicks < self.max_clicks:
            self.clicks += 1
        else:
            self.slide_index = min(self.slide_index + 1, self.deck.total - 1)
            self.clicks = 0
        self.broadcast()

    def prev(self):
        if self.clicks > 0:
            self.clicks -= 1
        else:
            self.slide_index = max(self.slide_index - 1, 0)
            self.clicks = self.current_slide.max_clicks
        self.broadcast()

    def reload_deck(self, new_deck):
        self.deck = new_deck
        self.slide_index = min(self.slide_index, new_deck.total - 1)
        self.clicks = min(self.clicks, self.current_slide.max_clicks)

    def apply_and_broadcast_changes(self, slide_index: int, changes: list[dict]):
        self.drawing.apply_changes(slide_index, changes)
        self.relay.emit_script(_drawing_script(_AUDIENCE_CANVAS, json.dumps(changes)))


def _yield_presenter_with_snapshot(pres):
    snapshot = pres.drawing.get_snapshot(pres.slide_index)
    yield from yield_presenter_updates(pres.deck, pres.slide_index, pres.clicks, drawing_snapshot=snapshot)


def yield_audience_updates(deck, slide_idx: int, clicks: int = 0):
    current_slide = deck.slides[slide_idx]
    # Elements first — replace stale data-class bindings before signals change
    yield elements(render_slide(current_slide, deck), "#slide-content", "inner")
    yield signals(slide_index=slide_idx, clicks=clicks, max_clicks=current_slide.max_clicks)


def yield_presenter_updates(deck, slide_idx: int, clicks: int = 0, *, drawing_snapshot: list[dict] | None = None):
    current_slide = deck.slides[slide_idx]
    next_slide = deck.slides[slide_idx + 1] if slide_idx + 1 < deck.total else None

    yield signals(slide_index=slide_idx, clicks=clicks, max_clicks=current_slide.max_clicks)
    yield elements(render_slide(current_slide, deck), "#presenter-slide-content", "inner")
    yield elements(
        render_slide(next_slide, deck) if next_slide else Div("End of presentation"),
        "#presenter-next",
        "inner",
    )
    yield elements(
        Div(current_slide.note or "No notes for this slide.", cls="presenter-notes-text"),
        "#presenter-notes-content",
        "inner",
    )

    if drawing_snapshot is not None:
        snapshot_json = json.dumps(drawing_snapshot) if drawing_snapshot else "[]"
        yield execute_script(_drawing_script("drawing-canvas", snapshot_json, clear=True))


def create_app(deck_path: Path, *, theme: str = "default", watch: bool = False):
    deck_path = deck_path.resolve()
    has_clicks = deck_has_clicks(deck_path)
    initial_deck = parse_deck(deck_path, use_motion=has_clicks)
    presenter_token = secrets.token_urlsafe(16)
    deck_state = {
        "deck": initial_deck,
        "path": deck_path,
        "watch": watch,
        "presentation": PresentationState(initial_deck),
        "presenter_token": presenter_token,
    }

    watch_lifespan = None
    if watch:
        deck_state["watch_relay"] = Relay()

        def _on_file_change():
            deck_state["watch_relay"].emit_signals({"file_version": int(time.time() * 1000)})

        watcher = FileWatcher(deck_path, _on_file_change)

        @asynccontextmanager
        async def watch_lifespan(app):
            task = asyncio.create_task(watcher.start())
            yield
            watcher.stop()
            task.cancel()

    app, rt = star_app(
        title=initial_deck.config.title,
        hdrs=deck_hdrs(theme),
        live=False,
        lifespan=watch_lifespan,
    )
    app.register(DrawingCanvas)
    if has_clicks or watch:
        app.register(motion)
    app.register(resize)

    assets_dir = deck_path.parent / "assets"
    if assets_dir.is_dir():
        app.register_package_static("deck_assets", str(assets_dir), "/assets")

    hash_nav_js = js("""
        const hash = window.location.hash;
        if (hash && hash.length > 1) {
            const parts = hash.substring(1).split('.');
            const slideNum = parseInt(parts[0], 10);
            const clickNum = parts.length > 1 ? parseInt(parts[1], 10) : 0;
            if (!isNaN(slideNum) && slideNum >= 1 && slideNum <= $total_slides) {
                @get('/api/slide/' + (slideNum - 1) + '?clicks=' + clickNum)
            }
        }
    """)

    @rt("/")
    def home():
        pres = deck_state["presentation"]
        deck = deck_state["deck"]

        slide_index = Signal("slide_index", pres.slide_index)
        total_slides = Signal("total_slides", deck.total)
        clicks = Signal("clicks", pres.clicks)
        max_clicks = Signal("max_clicks", pres.current_slide.max_clicks)
        slide_scale = Signal("slide_scale", 1)
        grid_open = Signal("grid_open", False)

        vis_signals = build_click_signals(deck, clicks)

        is_right = (evt.key == "ArrowRight") | (evt.key == " ")
        is_left = evt.key == "ArrowLeft"
        is_grid_key = (evt.key == "g") | (evt.key == "o")
        is_esc = evt.key == "Escape"
        not_grid = ~grid_open
        can_click_fwd = clicks < max_clicks
        can_click_back = clicks > 0

        grid_cards = build_grid_cards(
            deck,
            slide_index,
            grid_open,
            lambda idx: f"/api/slide/{idx}",
        )

        return Div(
            slide_index,
            total_slides,
            clicks,
            max_clicks,
            grid_open,
            *vis_signals,
            Span(data_on_load=get("/api/events"), style="display:none"),
            Span(data_on_load=hash_nav_js, style="display:none"),
            Span(data_on_hashchange=(hash_nav_js, {"window": True}), style="display:none"),
            Div(
                slide_scale,
                Div(
                    Div(render_slide(pres.current_slide, deck), id="slide-content"),
                    DrawingCanvas(
                        readonly=True,
                        id="audience-canvas",
                        style="position:absolute;inset:0;width:100%;height:100%;pointer-events:none;z-index:100;",
                        viewbox_width=VIEWBOX_WIDTH,
                        viewbox_height=VIEWBOX_HEIGHT,
                    ),
                    cls="slide-scaler",
                    data_attr_style="transform: translate(-50%, -50%) scale(" + slide_scale + ")",
                ),
                cls="slide-viewport",
                data_resize=slide_scale.set(
                    (js("$resize_width") / SLIDE_WIDTH).min(js("$resize_height") / SLIDE_HEIGHT)
                ),
            ),
            build_grid_modal(grid_cards, grid_open, "stardeck-root"),
            Div(
                Button(
                    "←",
                    cls="nav-btn",
                    data_on_click=can_click_back.if_(clicks.sub(1), get("/api/slide/prev")),
                    data_attr_disabled=slide_index == 0,
                ),
                Button(
                    data_text=slide_index + 1 + " / " + total_slides,
                    cls="slide-counter",
                    data_on_click=grid_open.toggle(),
                ),
                Button(
                    "→",
                    cls="nav-btn",
                    data_on_click=can_click_fwd.if_(clicks.add(1), get("/api/slide/next")),
                    data_attr_disabled=slide_index == total_slides - 1,
                ),
                cls="navigation-bar",
            ),
            Span(
                data_on_keydown=(
                    [
                        is_grid_key.then(seq(evt.preventDefault(), grid_open.toggle())),
                        (is_esc & grid_open).then(seq(evt.preventDefault(), grid_open.set(False))),
                        (not_grid & is_right).then(seq(
                            evt.preventDefault(),
                            can_click_fwd.if_(clicks.add(1), get("/api/slide/next")),
                        )),
                        (not_grid & is_left).then(seq(
                            evt.preventDefault(),
                            can_click_back.if_(clicks.sub(1), get("/api/slide/prev")),
                        )),
                    ],
                    {"window": True},
                ),
                style="display:none",
            ),
            Span(data_effect=HASH_UPDATE_EFFECT, style="display:none"),
            (file_version := Signal("file_version", 0)) if watch else None,
            Span(data_on_load=get("/api/watch-events"), style="display:none") if watch else None,
            Span(data_effect=(file_version > 0).then(get("/api/reload")), style="display:none") if watch else None,
            cls="stardeck-root",
        )

    @rt("/presenter")
    def presenter(token: str = ""):
        if token != deck_state["presenter_token"]:
            return Div(
                Div("Access Denied", style="font-size:2rem;color:#f44;margin-bottom:1rem"),
                Div("Presenter mode requires a valid token.", style="color:#888"),
                style="display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;background:#121212;font-family:system-ui",
            )
        return create_presenter_view(deck_state["deck"], deck_state["presentation"], token=token)

    @rt("/api/events")
    async def events():
        pres = deck_state["presentation"]
        # No initial signals — HTML already has correct state, and sending them
        # here races with hash navigation, resetting clicks to 0.
        initial = []
        snapshot = pres.drawing.get_snapshot(pres.slide_index)
        if snapshot:
            initial.append(ScriptEvent(_drawing_script(_AUDIENCE_CANVAS, json.dumps(snapshot))))
        return StreamingResponse(
            _sse_stream(pres.relay, initial),
            media_type="text/event-stream",
            headers=SSE_HEADERS,
        )

    @rt("/api/presenter/next")
    @sse
    def presenter_next():
        pres = deck_state["presentation"]
        pres.next()
        yield from _yield_presenter_with_snapshot(pres)

    @rt("/api/presenter/prev")
    @sse
    def presenter_prev():
        pres = deck_state["presentation"]
        pres.prev()
        yield from _yield_presenter_with_snapshot(pres)

    @rt("/api/presenter/goto/{idx}")
    @sse
    def presenter_goto(idx: int, clicks: int = 0):
        pres = deck_state["presentation"]
        pres.goto_slide(idx, clicks)
        yield from _yield_presenter_with_snapshot(pres)

    @rt("/api/presenter/changes", methods=["POST"])
    async def presenter_changes(token: str, request):
        if token != deck_state["presenter_token"]:
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        try:
            body = await request.json()
        except (json.JSONDecodeError, ValueError):
            return JSONResponse({"error": "invalid JSON"}, status_code=400)
        changes = body.get("changes", [])
        if not changes:
            return JSONResponse({"ok": True, "applied": 0})
        pres = deck_state["presentation"]
        slide_index = body.get("slide_index", pres.slide_index)
        pres.apply_and_broadcast_changes(slide_index, changes)
        return JSONResponse({"ok": True, "applied": len(changes)})

    @rt("/api/slide/next")
    @sse
    def next_slide(slide_index: int = 0):
        current_deck = deck_state["deck"]
        yield from yield_audience_updates(current_deck, min(slide_index + 1, current_deck.total - 1))

    @rt("/api/slide/prev")
    @sse
    def prev_slide(slide_index: int = 0):
        current_deck = deck_state["deck"]
        yield from yield_audience_updates(current_deck, max(slide_index - 1, 0))

    @rt("/api/slide/{idx}")
    @sse
    def goto_slide(idx: int, clicks: int = 0):
        current_deck = deck_state["deck"]
        idx = max(0, min(idx, current_deck.total - 1))
        clicks = max(0, min(clicks, current_deck.slides[idx].max_clicks))
        yield from yield_audience_updates(current_deck, idx, clicks)

    def _signal_deps(deck):
        """Hashable fingerprint of signals needed for a deck."""
        mc = max((s.max_clicks for s in deck.slides), default=0)
        ranges = frozenset().union(*(s.range_clicks for s in deck.slides)) if deck.slides else frozenset()
        return mc, ranges

    @rt("/api/reload")
    @sse
    def reload_deck(slide_index: int = 0):
        old_mc, old_ranges = _signal_deps(deck_state["deck"])
        use_motion = deck_has_clicks(deck_state["path"])
        current_deck = parse_deck(deck_state["path"], use_motion=use_motion)
        deck_state["deck"] = current_deck
        deck_state["presentation"].reload_deck(current_deck)
        new_mc, new_ranges = _signal_deps(current_deck)

        if new_mc > old_mc or new_ranges - old_ranges:
            yield execute_script("window.location.reload()")
            return

        idx = min(slide_index, current_deck.total - 1)
        yield signals(total_slides=current_deck.total)
        yield from yield_audience_updates(current_deck, idx)

    @rt("/api/watch-events")
    async def watch_events():
        relay = deck_state.get("watch_relay")
        if not relay:
            return JSONResponse({"error": "watch not enabled"}, status_code=404)
        return StreamingResponse(
            _sse_stream(relay),
            media_type="text/event-stream",
            headers=SSE_HEADERS,
        )

    return app, rt, deck_state
