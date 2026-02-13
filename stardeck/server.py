"""StarDeck server application."""

import asyncio
import json
import secrets
import time
from pathlib import Path

from starhtml import (
    Button,
    Div,
    Link,
    Relay,
    Script,
    ScriptEvent,
    Signal,
    SignalEvent,
    Span,
    Style,
    elements,
    execute_script,
    format_event,
    get,
    iconify_script,
    signals,
    sse,
    star_app,
)
from starhtml.plugins import resize
from starhtml.datastar import js
from starhtml.realtime import SSE_HEADERS
from star_drawing import DrawingCanvas
from starlette.responses import JSONResponse, StreamingResponse

from stardeck.drawing_relay import DrawingStore
from stardeck.parser import parse_deck
from stardeck.presenter import create_presenter_view
from stardeck.renderer import render_slide
from stardeck.themes import get_theme_css

_AUDIENCE_CANVAS = "#audience-canvas"


def _audience_drawing_script(snapshot: list[dict], *, clear: bool = True) -> str:
    """JS to load a drawing snapshot onto the audience canvas."""
    snapshot_json = json.dumps(snapshot) if snapshot else "[]"
    clear_call = "c.clear();" if clear else ""
    return (
        f"(()=>{{const c=document.querySelector('{_AUDIENCE_CANVAS}');"
        f"if(!c||!c.applyRemoteChanges)return;"
        f"{clear_call}c.applyRemoteChanges({snapshot_json})}})()"
    )


class PresentationState:
    """Server-side presentation state with Relay-based presenter→audience broadcast."""

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
        self.relay.emit_signals({
            "slide_index": self.slide_index,
            "clicks": self.clicks,
            "max_clicks": self.max_clicks,
        })
        self.relay.emit_element(render_slide(self.current_slide, self.deck), "#slide-content")
        snapshot = self.drawing.get_snapshot(self.slide_index)
        self.relay.emit_script(_audience_drawing_script(snapshot))

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
        changes_json = json.dumps(changes)
        self.relay.emit_script(
            f"(()=>{{const c=document.querySelector('{_AUDIENCE_CANVAS}');"
            f"if(c&&c.applyRemoteChanges)c.applyRemoteChanges({changes_json})}})()"
        )


def yield_audience_updates(deck, slide_idx: int, clicks: int = 0):
    current_slide = deck.slides[slide_idx]
    yield signals(slide_index=slide_idx, clicks=clicks, max_clicks=current_slide.max_clicks)
    yield elements(render_slide(current_slide, deck), "#slide-content", "inner")


def yield_presenter_updates(deck, slide_idx: int, clicks: int = 0, *, drawing_snapshot: list[dict] | None = None):
    current_slide = deck.slides[slide_idx]
    next_slide = deck.slides[slide_idx + 1] if slide_idx + 1 < deck.total else None

    yield signals(slide_index=slide_idx, clicks=clicks, max_clicks=current_slide.max_clicks)
    yield elements(render_slide(current_slide, deck), "#presenter-slide-content", "inner")
    yield elements(
        render_slide(next_slide, deck) if next_slide else Div("End of presentation"),
        "#presenter-next", "inner",
    )
    yield elements(
        Div(current_slide.note or "No notes for this slide.", cls="presenter-notes-text"),
        "#presenter-notes-content", "inner",
    )

    if drawing_snapshot is not None:
        snapshot_json = json.dumps(drawing_snapshot) if drawing_snapshot else "[]"
        yield execute_script(
            f"(()=>{{const c=document.querySelector('drawing-canvas');"
            f"if(c){{c.clear();c.applyRemoteChanges({snapshot_json})}}}})()"
        )


def create_app(deck_path: Path, *, theme: str = "default", watch: bool = False):
    initial_deck = parse_deck(deck_path)
    presenter_token = secrets.token_urlsafe(16)
    deck_state = {
        "deck": initial_deck,
        "path": deck_path,
        "watch": watch,
        "reload_timestamp": int(time.time() * 1000),
        "presentation": PresentationState(initial_deck),
        "presenter_token": presenter_token,
    }
    theme_css = get_theme_css(theme)
    deck = deck_state["deck"]

    app, rt = star_app(
        title=deck.config.title,
        hdrs=[
            Script(src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"),
            iconify_script(),
            Link(rel="stylesheet", href="https://fonts.googleapis.com/css2?family=Shantell+Sans:wght@400;700&display=swap"),
            Style(theme_css),
        ],
        live=False,
    )
    app.register(DrawingCanvas)
    app.register(resize)

    assets_dir = deck_path.parent / "assets"
    if assets_dir.is_dir():
        app.register_package_static("deck_assets", str(assets_dir), "/assets")

    @rt("/")
    def home():
        pres = deck_state["presentation"]
        initial_slide = pres.current_slide

        slide_index = Signal("slide_index", pres.slide_index)
        total_slides = Signal("total_slides", deck.total)
        slide_scale = Signal("slide_scale", 1)
        grid_open = Signal("grid_open", False)

        grid_cards = []
        for slide in deck.slides:
            idx = slide.index
            grid_cards.append(
                Div(
                    Div(
                        render_slide(slide, deck),
                        cls="grid-slide-inner",
                    ),
                    Span(str(idx + 1), cls="grid-slide-number"),
                    cls="grid-slide-card",
                    data_class_current=slide_index == idx,
                    data_on_click=[grid_open.set(False), get(f"/api/slide/{idx}")],
                ),
            )

        return Div(
            slide_index,
            total_slides,
            Signal("clicks", pres.clicks),
            Signal("max_clicks", initial_slide.max_clicks),
            grid_open,
            # Long-lived SSE for presenter→audience sync
            Span(data_on_load="@get('/api/events')", style="display:none"),
            # Deep-link: parse #slide or #slide.click on load
            Span(
                data_on_load=js("""
                    const hash = window.location.hash;
                    if (hash && hash.length > 1) {
                        const parts = hash.substring(1).split('.');
                        const slideNum = parseInt(parts[0], 10);
                        const clickNum = parts.length > 1 ? parseInt(parts[1], 10) : 0;
                        if (!isNaN(slideNum) && slideNum >= 1 && slideNum <= $total_slides) {
                            @get('/api/slide/' + (slideNum - 1) + '?clicks=' + clickNum)
                        }
                    }
                """),
                style="display:none",
            ),
            Span(
                data_on_hashchange=(
                    js("""
                    const hash = window.location.hash;
                    if (hash && hash.length > 1) {
                        const parts = hash.substring(1).split('.');
                        const slideNum = parseInt(parts[0], 10);
                        const clickNum = parts.length > 1 ? parseInt(parts[1], 10) : 0;
                        if (!isNaN(slideNum) && slideNum >= 1 && slideNum <= $total_slides) {
                            @get('/api/slide/' + (slideNum - 1) + '?clicks=' + clickNum)
                        }
                    }
                    """),
                    {"window": True},
                ),
                style="display:none",
            ),
            Div(
                slide_scale,
                Div(
                    Div(render_slide(deck.slides[0], deck), id="slide-content"),
                    DrawingCanvas(readonly=True, id="audience-canvas", style="position:absolute;inset:0;width:100%;height:100%;pointer-events:none;z-index:100;", viewbox_width=160, viewbox_height=90),
                    cls="slide-scaler",
                    data_attr_style="transform: translate(-50%, -50%) scale(" + slide_scale + ")",
                ),
                cls="slide-viewport",
                data_resize=slide_scale.set(
                    (js("$resize_width") / 1920).min(js("$resize_height") / 1080)
                ),
            ),
            Div(
                Div(*grid_cards, cls="grid-container"),
                cls="overview-grid-modal",
                data_class_active=grid_open,
                data_on_click=js("if (evt.target === this) $grid_open = false"),
                data_effect=js("""
                    if ($grid_open) {
                        requestAnimationFrame(() => {
                            const root = document.querySelector('.stardeck-root');
                            const sw = parseFloat(getComputedStyle(root).getPropertyValue('--slide-width'));
                            document.querySelectorAll('.grid-slide-card').forEach(card => {
                                const inner = card.querySelector('.grid-slide-inner');
                                if (inner) inner.style.transform = 'scale(' + (card.offsetWidth / sw) + ')';
                            });
                        });
                    }
                """),
            ),
            Div(
                Button("←", cls="nav-btn", data_on_click=get("/api/slide/prev"), data_attr_disabled=slide_index == 0),
                Button(data_text=slide_index + 1 + " / " + total_slides, cls="slide-counter", data_on_click=grid_open.toggle()),
                Button("→", cls="nav-btn", data_on_click=get("/api/slide/next"), data_attr_disabled=slide_index == total_slides - 1),
                cls="navigation-bar",
            ),
            Span(
                data_on_keydown=(
                    js("""
                    if (evt.key === 'g' || evt.key === 'o') {
                        evt.preventDefault();
                        $grid_open = !$grid_open;
                    } else if (evt.key === 'Escape') {
                        if ($grid_open) { evt.preventDefault(); $grid_open = false; }
                    } else if (!$grid_open) {
                        if (evt.key === 'ArrowRight' || evt.key === ' ') {
                            evt.preventDefault();
                            if ($clicks < $max_clicks) {
                                $clicks++;
                            } else {
                                $clicks = 0;
                                @get('/api/slide/next');
                            }
                        } else if (evt.key === 'ArrowLeft') {
                            evt.preventDefault();
                            if ($clicks > 0) {
                                $clicks--;
                            } else {
                                @get('/api/slide/prev');
                            }
                        }
                    }
                    """),
                    {"window": True},
                ),
                style="display:none",
            ),
            Span(
                data_effect=js("window.history.replaceState(null, '', '#' + ($slide_index + 1) + ($clicks > 0 ? '.' + $clicks : ''))"),
                style="display:none",
            ),
            Span(
                Signal("watch_ts", deck_state["reload_timestamp"]),
                data_on_interval=(
                    js("""
                    fetch('/api/watch-status')
                        .then(r => r.json())
                        .then(data => {
                            if (data.timestamp > $watch_ts) {
                                $watch_ts = data.timestamp;
                                @get('/api/reload')
                            }
                        })
                    """),
                    {"duration": "1s"},
                ),
                style="display:none",
            ) if deck_state.get("watch") else None,
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

    # --- Broadcast sync: presenter→audience via Relay ---

    @rt("/api/events")
    async def events():
        pres = deck_state["presentation"]
        queue = pres.relay.subscribe()

        async def event_stream():
            try:
                # Initial state for late-joiners
                yield format_event(SignalEvent({
                    "slide_index": pres.slide_index,
                    "clicks": pres.clicks,
                    "max_clicks": pres.max_clicks,
                    "total_slides": pres.deck.total,
                }))
                snapshot = pres.drawing.get_snapshot(pres.slide_index)
                if snapshot:
                    yield format_event(ScriptEvent(_audience_drawing_script(snapshot, clear=False)))

                while True:
                    try:
                        event = await asyncio.wait_for(queue.get(), timeout=30.0)
                        yield format_event(event)
                    except asyncio.TimeoutError:
                        yield ": keepalive\n\n"

            except asyncio.CancelledError:
                pass
            finally:
                pres.relay.unsubscribe(queue)

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers=SSE_HEADERS,
        )

    @rt("/api/presenter/next")
    @sse
    def presenter_next():
        pres = deck_state["presentation"]
        pres.next()
        snapshot = pres.drawing.get_snapshot(pres.slide_index)
        yield from yield_presenter_updates(pres.deck, pres.slide_index, pres.clicks, drawing_snapshot=snapshot)

    @rt("/api/presenter/prev")
    @sse
    def presenter_prev():
        pres = deck_state["presentation"]
        pres.prev()
        snapshot = pres.drawing.get_snapshot(pres.slide_index)
        yield from yield_presenter_updates(pres.deck, pres.slide_index, pres.clicks, drawing_snapshot=snapshot)

    @rt("/api/presenter/goto/{idx}")
    @sse
    def presenter_goto(idx: int, clicks: int = 0):
        pres = deck_state["presentation"]
        pres.goto_slide(idx, clicks)
        snapshot = pres.drawing.get_snapshot(pres.slide_index)
        yield from yield_presenter_updates(pres.deck, pres.slide_index, pres.clicks, drawing_snapshot=snapshot)

    @rt("/api/presenter/changes", methods=["POST"])
    async def presenter_changes(token: str, request):
        if token != deck_state["presenter_token"]:
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        body = await request.json()
        changes = body.get("changes", [])
        if not changes:
            return JSONResponse({"ok": True, "applied": 0})
        pres = deck_state["presentation"]
        slide_index = body.get("slide_index", pres.slide_index)
        pres.apply_and_broadcast_changes(slide_index, changes)
        return JSONResponse({"ok": True, "applied": len(changes)})

    # --- Local navigation (individual client, no broadcast) ---

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

    @rt("/api/reload")
    @sse
    def reload_deck(slide_index: int = 0):
        deck_state["deck"] = parse_deck(deck_state["path"])
        current_deck = deck_state["deck"]
        idx = min(slide_index, current_deck.total - 1)
        yield signals(total_slides=current_deck.total)
        yield from yield_audience_updates(current_deck, idx)

    @rt("/api/watch-status")
    def watch_status():
        return JSONResponse({"timestamp": deck_state.get("reload_timestamp", 0)})

    return app, rt, deck_state
