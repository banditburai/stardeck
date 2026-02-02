"""StarDeck server application."""

import asyncio
import secrets
import time
from pathlib import Path

from starhtml import (
    Button,
    Div,
    Script,
    Signal,
    Span,
    Style,
    Svg,
    elements,
    get,
    signals,
    sse,
    star_app,
)
from fastcore.xml import to_xml
from starlette.responses import JSONResponse, StreamingResponse

from stardeck.drawing import DrawingElement, DrawingState
from stardeck.parser import parse_deck
from stardeck.presenter import create_presenter_view
from stardeck.renderer import render_slide
from stardeck.themes import get_theme_css


class PresentationState:
    """Server-side presentation state with pub/sub for broadcast sync.

    This enables true presenter→audience sync:
    - Presenter controls update the authoritative state
    - All connected audience clients receive broadcasts
    - One-way sync: presenter controls, audience follows
    """

    def __init__(self, deck):
        self.deck = deck
        self.slide_index = 0
        self.clicks = 0
        self.subscribers: list[asyncio.Queue] = []
        self._lock = asyncio.Lock()
        self.drawing = DrawingState()

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

    async def subscribe(self) -> asyncio.Queue:
        """Subscribe to state changes. Returns a queue that receives updates."""
        queue = asyncio.Queue()
        async with self._lock:
            self.subscribers.append(queue)
        return queue

    async def unsubscribe(self, queue: asyncio.Queue):
        """Unsubscribe from state changes."""
        async with self._lock:
            if queue in self.subscribers:
                self.subscribers.remove(queue)

    async def broadcast(self):
        """Broadcast current state to all subscribers."""
        async with self._lock:
            for queue in self.subscribers:
                try:
                    # Non-blocking put - drop if queue is full
                    queue.put_nowait({
                        "slide_index": self.slide_index,
                        "clicks": self.clicks,
                        "max_clicks": self.max_clicks,
                    })
                except asyncio.QueueFull:
                    pass  # Skip slow clients

    async def goto_slide(self, idx: int, clicks: int = 0):
        """Navigate to a specific slide and broadcast to all clients."""
        idx = max(0, min(idx, self.deck.total - 1))
        slide = self.deck.slides[idx]
        clicks = max(0, min(clicks, slide.max_clicks))

        self.slide_index = idx
        self.clicks = clicks
        await self.broadcast()

    async def next(self):
        """Go to next click or next slide."""
        if self.clicks < self.max_clicks:
            self.clicks += 1
        else:
            self.slide_index = min(self.slide_index + 1, self.deck.total - 1)
            self.clicks = 0
        await self.broadcast()

    async def prev(self):
        """Go to previous click or previous slide."""
        if self.clicks > 0:
            self.clicks -= 1
        else:
            self.slide_index = max(self.slide_index - 1, 0)
            # Go to last click of previous slide
            self.clicks = self.current_slide.max_clicks
        await self.broadcast()

    def reload_deck(self, new_deck):
        """Reload deck after file change."""
        self.deck = new_deck
        # Clamp current position to valid range
        self.slide_index = min(self.slide_index, new_deck.total - 1)
        self.clicks = min(self.clicks, self.current_slide.max_clicks)

    async def add_drawing(self, element: DrawingElement):
        """Add a drawing element and broadcast to all subscribers."""
        self.drawing.add_element(element)
        await self.broadcast_drawing(element)

    async def broadcast_drawing(self, element: DrawingElement):
        """Broadcast a drawing element to all subscribers."""
        async with self._lock:
            for queue in self.subscribers:
                try:
                    queue.put_nowait({
                        "type": "drawing",
                        "action": "add",
                        "element": element,
                    })
                except asyncio.QueueFull:
                    pass


def yield_audience_updates(deck, slide_idx: int, clicks: int = 0):
    """Yield SSE updates for audience view only."""
    current_slide = deck.slides[slide_idx]

    # Signal updates
    yield signals(slide_index=slide_idx, clicks=clicks, max_clicks=current_slide.max_clicks)

    # Audience view update
    yield elements(render_slide(current_slide, deck), "#slide-content", "inner")


def yield_presenter_updates(deck, slide_idx: int, clicks: int = 0):
    """Yield SSE updates for presenter view only."""
    current_slide = deck.slides[slide_idx]
    next_slide = deck.slides[slide_idx + 1] if slide_idx + 1 < deck.total else None

    # Signal updates
    yield signals(slide_index=slide_idx, clicks=clicks, max_clicks=current_slide.max_clicks)

    # Presenter view updates only
    yield elements(render_slide(current_slide, deck), "#presenter-current", "inner")
    yield elements(
        render_slide(next_slide, deck) if next_slide else Div("End of presentation"),
        "#presenter-next",
        "inner"
    )
    yield elements(
        Div(current_slide.note or "No notes for this slide.", cls="presenter-notes-text"),
        "#presenter-notes-content",
        "inner"
    )


def create_app(deck_path: Path, *, debug: bool = False, theme: str = "default", watch: bool = False):
    """Create a StarDeck application.

    Args:
        deck_path: Path to the markdown file.
        debug: Enable debug mode.
        theme: Theme name to use (default: "default").
        watch: Enable watch mode for hot reload on file changes.

    Returns:
        Tuple of (app, route_decorator, deck_state).
    """
    # Use mutable container so deck can be re-parsed on reload
    # reload_timestamp is used by watch mode to detect file changes
    initial_deck = parse_deck(deck_path)
    # Generate secure token for presenter access
    presenter_token = secrets.token_urlsafe(16)
    deck_state = {
        "deck": initial_deck,
        "path": deck_path,
        "watch": watch,
        "reload_timestamp": int(time.time() * 1000),
        "presentation": PresentationState(initial_deck),  # Server-side state for broadcast sync
        "presenter_token": presenter_token,  # Token for presenter authentication
    }
    theme_css = get_theme_css(theme)

    deck = deck_state["deck"]  # Initial deck reference
    pres = deck_state["presentation"]  # Presentation state reference

    app, rt = star_app(
        title=deck.config.title,
        hdrs=[
            Script(src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"),
            Style(theme_css),
        ],
        live=debug,
    )

    @rt("/")
    def home():
        # Get current state from presentation (for broadcast sync)
        pres = deck_state["presentation"]
        initial_slide = pres.current_slide

        return Div(
            (slide_index := Signal("slide_index", pres.slide_index)),
            (total_slides := Signal("total_slides", deck.total)),
            (clicks := Signal("clicks", pres.clicks)),
            (max_clicks := Signal("max_clicks", initial_slide.max_clicks)),
            # Subscribe to presenter broadcasts (long-lived SSE connection)
            # This enables true one-way sync: presenter controls, audience follows
            Span(
                data_init="@get('/api/events')",
                style="display: none",
            ),
            # URL hash navigation on load - uses Datastar's data-init
            # Supports #slide or #slide.click format (e.g., #3 or #3.2)
            # Note: This is for deep linking; once loaded, presenter controls via events
            Span(
                data_init="""
                    const hash = window.location.hash;
                    if (hash && hash.length > 1) {
                        const parts = hash.substring(1).split('.');
                        const slideNum = parseInt(parts[0], 10);
                        const clickNum = parts.length > 1 ? parseInt(parts[1], 10) : 0;
                        if (!isNaN(slideNum) && slideNum >= 1 && slideNum <= $total_slides) {
                            @get('/api/slide/' + (slideNum - 1) + '?clicks=' + clickNum)
                        }
                    }
                """,
                style="display: none",
            ),
            # URL hash change listener - handles manual URL changes and back/forward
            # Supports #slide or #slide.click format (e.g., #3 or #3.2)
            Span(
                data_on_hashchange=(
                    """
                    const hash = window.location.hash;
                    if (hash && hash.length > 1) {
                        const parts = hash.substring(1).split('.');
                        const slideNum = parseInt(parts[0], 10);
                        const clickNum = parts.length > 1 ? parseInt(parts[1], 10) : 0;
                        if (!isNaN(slideNum) && slideNum >= 1 && slideNum <= $total_slides) {
                            @get('/api/slide/' + (slideNum - 1) + '?clicks=' + clickNum)
                        }
                    }
                    """,
                    {"window": True},
                ),
                style="display: none",
            ),
            # Slide viewport (full screen)
            Div(
                render_slide(deck.slides[0], deck),
                # Drawing layer overlay (SVG for vector annotations)
                Svg(
                    id="drawing-layer",
                    cls="drawing-layer",
                    viewBox="0 0 100 100",
                    preserveAspectRatio="none",
                ),
                id="slide-content",
                cls="slide-viewport",
            ),
            # Navigation controls
            Div(
                Button(
                    "←",
                    cls="nav-btn",
                    data_on_click=get("/api/slide/prev"),
                    data_attr_disabled=slide_index == 0,
                ),
                Span(
                    data_text=slide_index + 1 + " / " + total_slides,
                    cls="slide-counter",
                ),
                Button(
                    "→",
                    cls="nav-btn",
                    data_on_click=get("/api/slide/next"),
                    data_attr_disabled=slide_index == total_slides - 1,
                ),
                cls="navigation-bar",
            ),
            # Keyboard navigation with click support (window-level)
            Span(
                data_on_keydown=(
                    """
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
                    """,
                    {"window": True},
                ),
                style="display: none",
            ),
            # URL hash update on navigation - uses Datastar effect (DS-005)
            # Format: #slide or #slide.click (e.g., #3 or #3.2)
            Span(
                data_effect="window.history.replaceState(null, '', '#' + ($slide_index + 1) + ($clicks > 0 ? '.' + $clicks : ''))",
                style="display: none",
            ),
            # Watch mode polling for hot reload (only when watch=True)
            Span(
                (watch_ts := Signal("watch_ts", deck_state["reload_timestamp"])),
                data_on_interval=(
                    """
                    fetch('/api/watch-status')
                        .then(r => r.json())
                        .then(data => {
                            if (data.timestamp > $watch_ts) {
                                $watch_ts = data.timestamp;
                                @get('/api/reload')
                            }
                        })
                    """,
                    {"duration": "1s"},
                ),
                style="display: none",
            ) if deck_state.get("watch") else None,
            cls="stardeck-root",
        )

    @rt("/presenter")
    def presenter(token: str = ""):
        """Presenter view - requires valid token for access."""
        if token != deck_state["presenter_token"]:
            return Div(
                Div(
                    "Access Denied",
                    style="font-size: 2rem; color: #f44; margin-bottom: 1rem;",
                ),
                Div(
                    "Presenter mode requires a valid token.",
                    style="color: #888;",
                ),
                style="display: flex; flex-direction: column; align-items: center; justify-content: center; height: 100vh; background: #121212; font-family: system-ui;",
            )
        return create_presenter_view(deck_state["deck"], deck_state["presentation"])

    # =========================================================================
    # Broadcast sync endpoints - True presenter→audience sync
    # =========================================================================

    @rt("/api/events")
    async def events():
        """SSE stream for broadcast sync. Audience clients subscribe here.

        This is a long-lived connection that receives updates whenever
        the presenter navigates. Enables true one-way sync.
        """
        pres = deck_state["presentation"]
        queue = await pres.subscribe()

        async def event_stream():
            try:
                deck = pres.deck

                # Send initial state immediately (Datastar SSE format)
                yield f"event: datastar-patch-signals\ndata: signals {{\"slide_index\": {pres.slide_index}, \"clicks\": {pres.clicks}, \"max_clicks\": {pres.max_clicks}, \"total_slides\": {deck.total}}}\n\n"

                # Wait for updates from presenter
                while True:
                    try:
                        # Wait for next state change (with timeout to keep connection alive)
                        state = await asyncio.wait_for(queue.get(), timeout=30.0)

                        # Send signal updates (Datastar format)
                        yield f"event: datastar-patch-signals\ndata: signals {{\"slide_index\": {state['slide_index']}, \"clicks\": {state['clicks']}, \"max_clicks\": {state['max_clicks']}}}\n\n"

                        # Send element updates for audience view
                        current = pres.current_slide
                        slide_html = to_xml(render_slide(current, deck))
                        # For SSE, multi-line content needs each line prefixed with "data: elements "
                        lines = slide_html.split("\n")
                        elements_data = "\n".join(f"data: elements {line}" for line in lines)
                        yield f"event: datastar-patch-elements\ndata: mode inner\ndata: selector #slide-content\n{elements_data}\n\n"

                    except asyncio.TimeoutError:
                        # Send keepalive comment
                        yield ": keepalive\n\n"

            except asyncio.CancelledError:
                pass
            finally:
                await pres.unsubscribe(queue)

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @rt("/api/presenter/next")
    @sse
    async def presenter_next():
        """Presenter navigation: next click or slide. Broadcasts to all audience."""
        pres = deck_state["presentation"]
        await pres.next()
        # Return updates for presenter view only (audience gets updates via /api/events)
        for update in yield_presenter_updates(pres.deck, pres.slide_index, pres.clicks):
            yield update

    @rt("/api/presenter/prev")
    @sse
    async def presenter_prev():
        """Presenter navigation: previous click or slide. Broadcasts to all audience."""
        pres = deck_state["presentation"]
        await pres.prev()
        # Return updates for presenter view only (audience gets updates via /api/events)
        for update in yield_presenter_updates(pres.deck, pres.slide_index, pres.clicks):
            yield update

    @rt("/api/presenter/goto/{idx}")
    @sse
    async def presenter_goto(idx: int, clicks: int = 0):
        """Presenter navigation: go to specific slide. Broadcasts to all audience."""
        pres = deck_state["presentation"]
        await pres.goto_slide(idx, clicks)
        # Return updates for presenter view only (audience gets updates via /api/events)
        for update in yield_presenter_updates(pres.deck, pres.slide_index, pres.clicks):
            yield update

    # =========================================================================
    # Local navigation endpoints - For individual client navigation
    # (does NOT broadcast to other clients)
    # =========================================================================

    @rt("/api/slide/next")
    @sse
    def next_slide(slide_index: int = 0):
        current_deck = deck_state["deck"]
        new_idx = min(slide_index + 1, current_deck.total - 1)
        yield from yield_audience_updates(current_deck, new_idx)

    @rt("/api/slide/prev")
    @sse
    def prev_slide(slide_index: int = 0):
        current_deck = deck_state["deck"]
        new_idx = max(slide_index - 1, 0)
        yield from yield_audience_updates(current_deck, new_idx)

    @rt("/api/slide/{idx}")
    @sse
    def goto_slide(idx: int, clicks: int = 0):
        current_deck = deck_state["deck"]
        idx = max(0, min(idx, current_deck.total - 1))
        new_slide = current_deck.slides[idx]
        # Clamp clicks to valid range for this slide
        clicks = max(0, min(clicks, new_slide.max_clicks))
        yield from yield_audience_updates(current_deck, idx, clicks)

    @rt("/api/reload")
    @sse
    def reload_deck(slide_index: int = 0):
        """Re-parse deck and re-render current slide after file change."""
        deck_state["deck"] = parse_deck(deck_state["path"])
        current_deck = deck_state["deck"]
        idx = min(slide_index, current_deck.total - 1)
        # Also update total_slides signal on reload
        yield signals(total_slides=current_deck.total)
        yield from yield_audience_updates(current_deck, idx)

    @rt("/api/watch-status")
    def watch_status():
        """Return current reload timestamp for watch mode polling."""
        return JSONResponse({"timestamp": deck_state.get("reload_timestamp", 0)})

    return app, rt, deck_state
