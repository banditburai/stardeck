# Stardeck Integration Plan: star-drawing Web Component

## Overview

Replace stardeck's homegrown drawing system (`drawing.py`, server-side SVG generation, server-side undo/redo, raw Datastar pointer handlers) with the `star-drawing` web component. The server becomes a dumb JSON relay — all drawing intelligence (tool handling, undo/redo, SVG rendering, coordinate math) lives client-side in the TypeScript controller.

**Net result:** ~500 lines removed, ~100 lines added. Four old endpoints collapse into one.

---

## Architecture

```
Presenter Browser                    Server                    Audience Browser
┌──────────────────┐          ┌──────────────────┐          ┌──────────────────┐
│ <drawing-canvas>  │          │   DrawingStore    │          │ <drawing-canvas   │
│   (interactive)   │  POST    │  (opaque JSON     │   SSE    │    readonly>      │
│                   │ -------> │   per-slide dict)  │ -------> │                   │
│ onElementChange   │ changes  │                   │ execute  │ applyRemoteChanges│
│  -> fetch POST    │          │ apply + broadcast  │ _script  │  -> render SVG    │
└──────────────────┘          └──────────────────┘          └──────────────────┘
```

**Key design decisions:**
- Server stores opaque JSON dicts — never parses element contents
- `datastar-execute-script` SSE events call `applyRemoteChanges()` on audience canvases
- Per-slide drawing persistence via `dict[int, dict[str, dict]]` keyed by slide index
- No server-side undo/redo — client emits the resulting change events naturally
- Phased migration: audience-side first (Phase A), then presenter-side (Phase B)

---

## Phase A: Audience-Side Swap + Server Relay

Keeps the old presenter drawing UI working while replacing the audience rendering and server data model.

### A1. Add star-drawing dependency

**File:** `stardeck/pyproject.toml`

```toml
[project]
dependencies = [
    "starhtml",
    "star-drawing",          # <-- ADD
    ...
]

[tool.uv.sources]
starhtml = { path = "../starhtml-upstream", editable = true }
star-drawing = { path = "../star-drawing", editable = true }   # <-- ADD
```

Then `uv sync`.

### A2. Register component + add iconify script

**File:** `stardeck/server.py`

```python
from star_drawing import DrawingCanvas

app, rt = star_app(
    title=deck.config.title,
    hdrs=[
        Script(src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"),
        iconify_script(),     # <-- for toolbar icons (needed in Phase B)
        Style(theme_css),
    ],
    live=debug,
)

app.register(DrawingCanvas)  # <-- serves /_pkg/star-drawing/ static files
```

### A3. Replace bare SVG with readonly DrawingCanvas

**File:** `stardeck/server.py`, `home()` function

**Critical:** The canvas must be a *sibling* of `#slide-content`, not a child. When the presenter navigates slides, Datastar replaces `#slide-content` innerHTML via `datastar-patch-elements`. A child canvas would be destroyed; a sibling persists.

Before:
```python
Div(
    render_slide(deck.slides[0], deck),
    Svg(id="drawing-layer", cls="drawing-layer", viewBox="0 0 100 100", ...),
    id="slide-content",
    cls="slide-viewport",
),
```

After:
```python
Div(
    Div(
        render_slide(deck.slides[0], deck),
        id="slide-content",
    ),
    DrawingCanvas(
        readonly=True,
        id="audience-canvas",
        cls="drawing-layer-canvas",
    ),
    cls="slide-viewport",
),
```

### A4. Add overlay CSS

**File:** `stardeck/themes/default/styles.css`

```css
.drawing-layer-canvas {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
    z-index: 100;
}
```

### A5. Server-side element store

**File:** `stardeck/server.py` (add to `PresentationState`) or new `stardeck/drawing_relay.py`

Replace `DrawingState` with a minimal opaque JSON store:

```python
@dataclass
class DrawingStore:
    """Per-slide opaque element storage. Server stores JSON dicts as-is."""
    slides: dict[int, dict[str, dict]] = field(default_factory=dict)
    element_order: dict[int, list[str]] = field(default_factory=dict)

    def apply_changes(self, slide_index: int, changes: list[dict]) -> None:
        if slide_index not in self.slides:
            self.slides[slide_index] = {}
            self.element_order[slide_index] = []
        elements = self.slides[slide_index]
        order = self.element_order[slide_index]
        for change in changes:
            t = change.get("type")
            if t in ("create", "update"):
                el = change["element"]
                eid = el["id"]
                elements[eid] = el
                if eid not in order:
                    order.append(eid)
            elif t == "delete":
                eid = change["elementId"]
                elements.pop(eid, None)
                if eid in order:
                    order.remove(eid)
            elif t == "reorder":
                self.element_order[slide_index] = [
                    eid for eid in change["order"] if eid in elements
                ]

    def get_snapshot(self, slide_index: int) -> list[dict]:
        if slide_index not in self.slides:
            return []
        elements = self.slides[slide_index]
        order = self.element_order.get(slide_index, [])
        if not elements:
            return []
        snapshot = [{"type": "create", "element": el} for el in elements.values()]
        if order:
            snapshot.append({"type": "reorder", "order": order})
        return snapshot
```

Update `PresentationState.__init__`: `self.drawing = DrawingStore()` (replaces old `DrawingState()`).

### A6. New endpoint: POST /api/presenter/changes

**File:** `stardeck/server.py`

```python
@rt("/api/presenter/changes", methods=["POST"])
async def presenter_changes(token: str, request):
    if token != deck_state["presenter_token"]:
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    body = await request.json()
    changes = body.get("changes", [])
    slide_index = body.get("slide_index", pres.slide_index)
    if not changes:
        return JSONResponse({"ok": True, "applied": 0})
    pres.drawing.apply_changes(slide_index, changes)
    # Broadcast to audience subscribers
    async with pres._lock:
        for queue in pres.subscribers:
            try:
                queue.put_nowait({"type": "drawing_changes", "changes": changes})
            except asyncio.QueueFull:
                pass
    return JSONResponse({"ok": True, "applied": len(changes)})
```

### A7. SSE changes — drawing broadcasts

**File:** `stardeck/server.py`, `/api/events` handler

Replace old `datastar-drawing` event handling with `datastar-execute-script`:

```python
if state.get("type") == "drawing_changes":
    changes_json = json.dumps(state["changes"])
    script = f"document.querySelector('#audience-canvas')?.applyRemoteChanges({changes_json})"
    yield f"event: datastar-execute-script\ndata: script {script}\n\n"
    continue
```

### A8. Late-joiner snapshot on SSE connect

At the start of `event_stream()`, after the initial signal patch:

```python
snapshot = pres.drawing.get_snapshot(pres.slide_index)
if snapshot:
    snapshot_json = json.dumps(snapshot)
    script = f"document.querySelector('#audience-canvas')?.applyRemoteChanges({snapshot_json})"
    yield f"event: datastar-execute-script\ndata: script {script}\n\n"
```

### A9. Clear + reload on slide navigation

When the audience receives a navigation event, clear the canvas and load the new slide's drawings:

```python
# After sending slide content update for navigation:
clear_and_load = "const c = document.querySelector('#audience-canvas'); if(c) { c.clear(); "
new_snapshot = pres.drawing.get_snapshot(state["slide_index"])
if new_snapshot:
    clear_and_load += f"c.applyRemoteChanges({json.dumps(new_snapshot)}); "
clear_and_load += "}"
yield f"event: datastar-execute-script\ndata: script {clear_and_load}\n\n"
```

### A10. Translation layer for old presenter endpoints

During Phase A, the old presenter still POSTs to `/api/presenter/draw`. Add a translation layer:

```python
# In existing /api/presenter/draw handler, after creating the element:
change = {"type": "create", "element": element_to_dict(drawing_element)}
pres.drawing.apply_changes(pres.slide_index, [change])
# Broadcast in new format
await broadcast_drawing_change([change])
```

Similarly for undo/redo/clear: convert the old operations to `ElementChangeEvent[]` before broadcasting.

### A11. Fix broken tests

| Test | Fix |
|------|-----|
| `test_drawing_layer_in_slide_viewport` | Assert `"drawing-canvas"` instead of `"<svg"` |
| `test_drawing_layer_has_arrow_marker` | Remove — markers are internal to the component |
| `test_presentation_state_has_drawing` | Update if `DrawingState` replaced with `DrawingStore` |

---

## Phase B: Presenter-Side Swap

Replace the old hand-rolled drawing layer and toolbar in `presenter.py` with the star-drawing component.

### B1. Remove old drawing code from presenter.py

**Delete entirely:**
- `COLORS` constant
- `create_drawing_layer(token)` (~130 lines of raw Datastar pointer handlers)
- `create_drawing_toolbar(token)` (~95 lines of emoji toolbar)
- Drawing-specific signals: `drawing_tool`, `stroke_color`, `stroke_width`, `_is_drawing`, `_draw_path`, `_start_x`, `_start_y`, `_points`

### B2. Add DrawingCanvas + toolbar to presenter view

```python
from star_drawing import DrawingCanvas, drawing_toolbar

def create_presenter_view(deck, pres=None, *, token=""):
    canvas = DrawingCanvas(
        name="presenter_drawing",
        style="position:absolute;inset:0;width:100%;height:100%;z-index:100;",
    )

    return Div(
        # ... existing navigation signals (unchanged) ...

        Div(
            # Current slide panel
            Div(
                render_slide(current_slide, deck),
                # Drawing canvas overlay (replaces create_drawing_layer)
                Div(
                    canvas,
                    id="drawing-canvas-wrapper",
                    data_on_element__change=js(f"""
                        fetch('/api/presenter/changes?token={token}', {{
                            method: 'POST',
                            headers: {{ 'Content-Type': 'application/json' }},
                            body: JSON.stringify({{
                                changes: evt.detail,
                                slide_index: $slide_index,
                            }}),
                        }});
                    """),
                ) if token else None,
                id="presenter-current",
                cls="presenter-slide-panel",
            ),
            # Info panel (unchanged)
            Div(...),
            cls="presenter-layout",
        ),

        # Drawing toolbar (replaces create_drawing_toolbar)
        drawing_toolbar(canvas) if token else None,

        cls="presenter-root",
    )
```

**Signal namespace:** With `name="presenter_drawing"`, the canvas signals become `presenter_drawing_tool`, `presenter_drawing_stroke_color`, etc. — no conflicts with stardeck's `slide_index`, `clicks`, etc.

**Event wiring:** The `data_on_element__change` Datastar attribute (double underscore = hyphen in event name) on the wrapper div catches the bubbling `element-change` CustomEvent and POSTs `evt.detail` (the `ElementChangeEvent[]`) to the server.

### B3. Presenter slide navigation — save/restore

When the presenter navigates slides, the canvas needs to clear and reload. Add drawing snapshot to presenter navigation endpoint responses:

```python
def _drawing_load_script(snapshot):
    snapshot_json = json.dumps(snapshot) if snapshot else "[]"
    script = f"const c = document.querySelector('drawing-canvas'); if(c) {{ c.clear(); c.applyRemoteChanges({snapshot_json}); }}"
    return f"event: datastar-execute-script\ndata: script {script}\n\n"
```

Yield this from `/api/presenter/next`, `/api/presenter/prev`, `/api/presenter/goto/{idx}` after the standard updates.

### B4. Delete old endpoints and drawing.py

| Delete | Reason |
|--------|--------|
| `POST /api/presenter/draw` | Replaced by `/api/presenter/changes` |
| `POST /api/presenter/draw/undo` | Client-side; results flow through `/changes` |
| `POST /api/presenter/draw/redo` | Same |
| `POST /api/presenter/draw/clear` | Same |
| `stardeck/drawing.py` (entire file) | Server no longer parses elements |
| `from stardeck.drawing import ...` | Dead import |

### B5. CSS cleanup

**Remove from `themes/default/styles.css`:**
- `.drawing-layer`, `.drawing-layer.active`
- `.drawing-toolbar`, `.toolbar-tools`, `.toolbar-actions`
- `.tool-btn`, `.tool-btn:hover`, `.tool-btn.active`
- `.color-palette`, `.color-btn`, `.color-btn.active`
- `.width-selector`, `.width-btn`

**Add:** star-drawing toolbar CSS (`.toolbar-island`, `.toolbar-bar`, etc.) from the star-drawing demo, adjusted for stardeck's dark theme.

**Override toolbar position for presenter:**
```css
.presenter-root .toolbar-island {
    position: fixed;
    bottom: 80px;
    top: auto;
    left: 50%;
    transform: translateX(-50%);
    z-index: 200;
}
```

### B6. Update presenter-related tests

Tests in `test_presenter.py` that check for `create_drawing_layer` or toolbar HTML will need updating.

---

## Open Questions

1. **`execute_script` in starhtml:** Does starhtml have a built-in `execute_script()` SSE helper, or do we emit raw SSE strings? Check starhtml source. Raw format works as fallback.

2. **`app.register(DrawingCanvas)` API:** Verify this is the correct method. The starelements framework should handle static file mounting, but needs testing.

3. **CSS layering:** Verify `position: absolute; inset: 0` on canvas works with existing `.slide-viewport` / `.presenter-slide-panel` styling (both have `position: relative`).

4. **Presenter save/restore timing:** When presenter clicks "next slide", any in-progress stroke is lost. This matches current behavior and is acceptable.

5. **Datastar signal access from Script:** The `$slide_index` expression works inside `data-on-*` attributes. For raw Script blocks, need `datastar.signals.slide_index` or DOM attribute access.

---

## File Change Summary

| File | Phase | Action |
|------|-------|--------|
| `pyproject.toml` | A | Add `star-drawing` dep + uv source |
| `server.py` — `create_app()` | A | `app.register(DrawingCanvas)`, add iconify script |
| `server.py` — `home()` | A | Replace SVG with `DrawingCanvas(readonly=True)` |
| `server.py` — `PresentationState` | A | Replace `DrawingState` with `DrawingStore` |
| `server.py` — new endpoint | A | `POST /api/presenter/changes` |
| `server.py` — `/api/events` | A | `execute_script` SSE, late-joiner snapshot, nav reload |
| `drawing_relay.py` | A | NEW: `DrawingStore` (~50 lines) |
| `themes/default/styles.css` | A | Add `.drawing-layer-canvas` overlay |
| `tests/test_drawing.py` | A | Fix 2-3 broken assertions |
| `presenter.py` | B | Replace drawing layer + toolbar with web component |
| `server.py` — old endpoints | B | Delete 4 old draw/undo/redo/clear endpoints |
| `drawing.py` | B | DELETE entire file (~400 lines) |
| `themes/default/styles.css` | B | Remove old toolbar CSS, add new |
