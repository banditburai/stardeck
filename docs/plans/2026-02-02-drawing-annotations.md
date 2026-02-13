# Drawing & Annotations Implementation Plan

> **Epic:** `stardeck-4u3`
> **Design:** `docs/designs/2026-02-02-drawing-annotations.md`
> **For Claude:** Use `skills/collaboration/execute-plan-with-beads` to implement.

## Tasks Overview

| ID | Task | Review ID | Blocked By |
|----|------|-----------|------------|
| stardeck-4u3.1 | Task 1: Drawing data models | stardeck-lth | - |
| stardeck-4u3.2 | Task 2: SVG drawing layer component | stardeck-t87 | .1 |
| stardeck-4u3.3 | Task 3: Pen tool implementation | stardeck-wfh | .2 |
| stardeck-4u3.4 | Task 4: Drawing state management | stardeck-0pn | .3 |
| stardeck-4u3.5 | Task 5: Presenter draw endpoints | stardeck-d6r | .4 |
| stardeck-4u3.6 | Task 6: SSE broadcast for drawings | stardeck-9rr | .5 |
| stardeck-4u3.7 | Task 7: Line tool | stardeck-64z | .3 |
| stardeck-4u3.8 | Task 8: Rectangle tool | stardeck-z0i | .3 |
| stardeck-4u3.9 | Task 9: Ellipse tool | stardeck-cdo | .3 |
| stardeck-4u3.10 | Task 10: Arrow tool | stardeck-tg1 | .7 |
| stardeck-4u3.11 | Task 11: Drawing toolbar UI | stardeck-wor | .3 |
| stardeck-4u3.12 | Task 12: Color picker | stardeck-ti6 | .11 |
| stardeck-4u3.13 | Task 13: Stroke width control | stardeck-bd4 | .11 |
| stardeck-4u3.14 | Task 14: Undo/Redo system | stardeck-bey | .4 |
| stardeck-4u3.15 | Task 15: Clear slide functionality | stardeck-97w | .4 |
| stardeck-4u3.16 | Task 16: Keyboard shortcuts | stardeck-6n8 | .11 |
| stardeck-4u3.17 | Task 17: Selection tool | stardeck-ueh | .4 |
| stardeck-4u3.18 | Task 18: Move elements | stardeck-2l4 | .17 |
| stardeck-4u3.19 | Task 19: Resize elements | stardeck-t8s | .17 |
| stardeck-4u3.20 | Task 20: Delete elements | stardeck-yaj | .17 |
| stardeck-4u3.21 | Task 21: Text tool | stardeck-5yr | .17 |
| stardeck-4u3.22 | Task 22: Diamond tool | stardeck-5fv | .8 |
| stardeck-4u3.23 | Task 23: Highlighter tool | stardeck-ui8 | .3 |
| stardeck-4u3.24 | Task 24: Eraser tool | stardeck-3zv | .17 |
| stardeck-4u3.25 | Task 25: Fill color support | stardeck-tur | .12 |
| stardeck-4u3.26 | Task 26: Opacity control | stardeck-38l | .11 |
| stardeck-4u3.27 | Task 27: Audience local notes layer | stardeck-3zu | .6 |
| stardeck-4u3.28 | Task 28: localStorage persistence | stardeck-71a | .27 |
| stardeck-4u3.29 | Task 29: My Notes toggle UI | stardeck-553 | .27 |
| stardeck-4u3.30 | Task 30: Export drawings | stardeck-kwh | .28 |

---

## Phase 1: Core Drawing (MVP)

### Task 1: Drawing Data Models

**Files:**
- Create: `stardeck/drawing.py`
- Test: `tests/test_drawing.py`

**Step 1: Write failing test**
```python
def test_drawing_element_creation():
    from stardeck.drawing import DrawingElement, PenElement, Point

    point = Point(x=10.0, y=20.0, pressure=0.5)
    assert point.x == 10.0

    element = PenElement(
        id="el-1",
        type="pen",
        stroke_color="#ff0000",
        stroke_width=2,
        points=[point],
        slide_index=0,
    )
    assert element.type == "pen"
    assert len(element.points) == 1
```

**Step 2: Verify test fails**
```bash
uv run pytest tests/test_drawing.py::test_drawing_element_creation -v
```

**Step 3: Implement**
Create dataclasses for:
- `Point` (x, y, pressure)
- `DrawingElement` (base class with id, type, colors, etc.)
- `PenElement` (freehand paths)
- `LineElement` (lines with optional arrows)
- `ShapeElement` (rect, ellipse, diamond)
- `TextElement` (text boxes)
- `DrawingState` (elements dict, undo/redo stacks)

**Step 4: Verify tests pass**
```bash
uv run pytest tests/test_drawing.py -v
```

---

### Task 2: SVG Drawing Layer Component

**Files:**
- Create: `stardeck/static/drawing.js`
- Modify: `stardeck/themes/default/styles.css`
- Test: Manual verification

**Step 1: Write failing test**
```python
def test_drawing_layer_in_slide_viewport(client):
    response = client.get("/")
    assert "drawing-layer" in response.text
    assert '<svg' in response.text
```

**Step 2: Implement**
Create SVG overlay component:
```javascript
// drawing.js - Drawing layer module
export class DrawingLayer {
    constructor(container) {
        this.svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        this.svg.setAttribute('class', 'drawing-layer');
        this.svg.setAttribute('viewBox', '0 0 100 100');
        this.svg.setAttribute('preserveAspectRatio', 'none');
        container.appendChild(this.svg);
    }

    addElement(element) { /* render element to SVG */ }
    removeElement(id) { /* remove by id */ }
    clear() { /* clear all elements */ }
}
```

Add CSS:
```css
.drawing-layer {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
    z-index: 100;
}
.drawing-layer.active {
    pointer-events: auto;
    cursor: crosshair;
}
```

**Step 3: Integrate into slide viewport**
Modify server.py to include drawing layer in slide-viewport div.

---

### Task 3: Pen Tool Implementation

**Files:**
- Modify: `stardeck/static/drawing.js`
- Test: `tests/test_drawing.py`

**Step 1: Write failing test**
```python
def test_pen_element_to_svg_path():
    from stardeck.drawing import PenElement, Point, element_to_svg

    element = PenElement(
        id="pen-1",
        type="pen",
        stroke_color="#ff0000",
        stroke_width=2,
        points=[Point(10, 20), Point(30, 40), Point(50, 30)],
        slide_index=0,
    )
    svg = element_to_svg(element)
    assert 'path' in svg
    assert 'stroke="#ff0000"' in svg
    assert 'M 10 20' in svg  # Move to start
```

**Step 2: Implement**
- Capture pointer events (pointerdown, pointermove, pointerup)
- Collect points into array
- Generate smooth SVG path with quadratic curves
- Render path element in real-time as user draws

**Step 3: Add path smoothing**
```javascript
function pointsToPath(points) {
    if (points.length < 2) return '';
    let d = `M ${points[0].x} ${points[0].y}`;
    for (let i = 1; i < points.length - 1; i++) {
        const xc = (points[i].x + points[i + 1].x) / 2;
        const yc = (points[i].y + points[i + 1].y) / 2;
        d += ` Q ${points[i].x} ${points[i].y} ${xc} ${yc}`;
    }
    d += ` L ${points[points.length - 1].x} ${points[points.length - 1].y}`;
    return d;
}
```

---

### Task 4: Drawing State Management

**Files:**
- Modify: `stardeck/server.py`
- Modify: `stardeck/drawing.py`
- Test: `tests/test_drawing.py`

**Step 1: Write failing test**
```python
def test_drawing_state_add_element():
    from stardeck.drawing import DrawingState, PenElement, Point

    state = DrawingState()
    element = PenElement(id="el-1", type="pen", stroke_color="#f00",
                         stroke_width=2, points=[Point(0,0)], slide_index=0)
    state.add_element(element)

    assert len(state.elements[0]) == 1
    assert state.elements[0][0].id == "el-1"
```

**Step 2: Implement**
Add to `PresentationState`:
```python
class PresentationState:
    def __init__(self, deck):
        # ... existing code ...
        self.drawing = DrawingState()

    async def add_drawing(self, element: DrawingElement):
        self.drawing.add_element(element)
        await self.broadcast_drawing(element)
```

---

### Task 5: Presenter Draw Endpoints

**Files:**
- Modify: `stardeck/server.py`
- Test: `tests/test_drawing.py`

**Step 1: Write failing test**
```python
def test_presenter_draw_endpoint(client, presenter_token):
    element_data = {
        "id": "el-1",
        "type": "pen",
        "stroke_color": "#ff0000",
        "stroke_width": 2,
        "points": [{"x": 10, "y": 20}],
        "slide_index": 0,
    }
    response = client.post(
        f"/api/presenter/draw?token={presenter_token}",
        json=element_data
    )
    assert response.status_code == 200
```

**Step 2: Implement endpoints**
```python
@rt("/api/presenter/draw")
@sse
async def presenter_draw(token: str, element: dict):
    """Add drawing element and broadcast to audience."""
    if token != deck_state["presenter_token"]:
        return {"error": "unauthorized"}

    pres = deck_state["presentation"]
    drawing_element = parse_element(element)
    await pres.add_drawing(drawing_element)

    # Return confirmation (audience gets update via /api/events)
    yield signals(drawing_added=True)
```

---

### Task 6: SSE Broadcast for Drawings

**Files:**
- Modify: `stardeck/server.py`
- Test: `tests/test_drawing.py`

**Step 1: Write failing test**
```python
def test_drawing_broadcast_in_events():
    # Test that /api/events includes drawing updates
    pass  # Integration test with SSE
```

**Step 2: Implement**
Extend `/api/events` to broadcast drawing changes:
```python
async def broadcast_drawing(self, element: DrawingElement):
    """Broadcast drawing element to all subscribers."""
    async with self._lock:
        for queue in self.subscribers:
            try:
                queue.put_nowait({
                    "type": "drawing",
                    "action": "add",
                    "element": element.to_dict(),
                })
            except asyncio.QueueFull:
                pass
```

Update event_stream to handle drawing events:
```python
if state.get("type") == "drawing":
    element_data = json.dumps(state["element"])
    yield f"event: datastar-drawing\ndata: {element_data}\n\n"
```

---

### Task 7: Line Tool

**Files:**
- Modify: `stardeck/static/drawing.js`
- Modify: `stardeck/drawing.py`
- Test: `tests/test_drawing.py`

**Step 1: Write failing test**
```python
def test_line_element_to_svg():
    from stardeck.drawing import LineElement, Point, element_to_svg

    element = LineElement(
        id="line-1",
        type="line",
        stroke_color="#0000ff",
        stroke_width=2,
        points=[Point(10, 10), Point(90, 90)],
        start_arrow=False,
        end_arrow=False,
        slide_index=0,
    )
    svg = element_to_svg(element)
    assert '<line' in svg
    assert 'x1="10"' in svg
```

**Step 2: Implement**
- Click to set start point
- Drag to preview line
- Release to finalize
- Render as SVG `<line>` element

---

### Task 8: Rectangle Tool

**Files:**
- Modify: `stardeck/static/drawing.js`
- Modify: `stardeck/drawing.py`
- Test: `tests/test_drawing.py`

**Step 1: Write failing test**
```python
def test_rect_element_to_svg():
    from stardeck.drawing import ShapeElement, element_to_svg

    element = ShapeElement(
        id="rect-1",
        type="rect",
        x=10, y=10, width=50, height=30,
        stroke_color="#00ff00",
        stroke_width=2,
        fill_color=None,
        slide_index=0,
    )
    svg = element_to_svg(element)
    assert '<rect' in svg
    assert 'width="50"' in svg
```

**Step 2: Implement**
- Click to set corner
- Drag to size rectangle (show preview)
- Release to finalize
- Shift key constrains to square

---

### Task 9: Ellipse Tool

**Files:**
- Modify: `stardeck/static/drawing.js`
- Modify: `stardeck/drawing.py`
- Test: `tests/test_drawing.py`

**Step 1: Write failing test**
```python
def test_ellipse_element_to_svg():
    from stardeck.drawing import ShapeElement, element_to_svg

    element = ShapeElement(
        id="ellipse-1",
        type="ellipse",
        x=50, y=50, width=40, height=20,
        stroke_color="#ff00ff",
        stroke_width=2,
        fill_color=None,
        slide_index=0,
    )
    svg = element_to_svg(element)
    assert '<ellipse' in svg
    assert 'rx="20"' in svg  # half of width
```

**Step 2: Implement**
- Similar to rectangle but renders as `<ellipse>`
- Shift key constrains to circle

---

### Task 10: Arrow Tool

**Files:**
- Modify: `stardeck/static/drawing.js`
- Modify: `stardeck/drawing.py`
- Test: `tests/test_drawing.py`

**Step 1: Write failing test**
```python
def test_arrow_element_to_svg():
    from stardeck.drawing import LineElement, Point, element_to_svg

    element = LineElement(
        id="arrow-1",
        type="arrow",
        stroke_color="#000",
        stroke_width=2,
        points=[Point(10, 50), Point(90, 50)],
        start_arrow=False,
        end_arrow=True,
        slide_index=0,
    )
    svg = element_to_svg(element)
    assert 'marker-end' in svg  # Arrow marker reference
```

**Step 2: Implement**
- Extend line tool with arrowhead markers
- Define SVG `<marker>` for arrowhead
- Apply marker-end to line element

---

### Task 11: Drawing Toolbar UI

**Files:**
- Modify: `stardeck/presenter.py`
- Modify: `stardeck/themes/default/styles.css`
- Test: Manual verification

**Step 1: Create toolbar component**
```python
def create_drawing_toolbar():
    return Div(
        # Tool buttons
        Div(
            Button("✏️", data_on_click="$drawing_tool = 'pen'", cls="tool-btn"),
            Button("📏", data_on_click="$drawing_tool = 'line'", cls="tool-btn"),
            Button("⬜", data_on_click="$drawing_tool = 'rect'", cls="tool-btn"),
            Button("⭕", data_on_click="$drawing_tool = 'ellipse'", cls="tool-btn"),
            Button("➡️", data_on_click="$drawing_tool = 'arrow'", cls="tool-btn"),
            cls="toolbar-tools"
        ),
        # Actions
        Div(
            Button("↩️", data_on_click="@post('/api/presenter/draw/undo')", cls="tool-btn"),
            Button("↪️", data_on_click="@post('/api/presenter/draw/redo')", cls="tool-btn"),
            Button("🗑️", data_on_click="@post('/api/presenter/draw/clear')", cls="tool-btn"),
            cls="toolbar-actions"
        ),
        cls="drawing-toolbar",
        id="drawing-toolbar",
    )
```

**Step 2: Add CSS styling**
```css
.drawing-toolbar {
    position: fixed;
    bottom: 80px;
    left: 50%;
    transform: translateX(-50%);
    background: var(--bg-dark);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 8px;
    display: flex;
    gap: 8px;
    z-index: 200;
}
```

---

### Task 12: Color Picker

**Files:**
- Modify: `stardeck/static/drawing.js`
- Modify: `stardeck/presenter.py`
- Test: Manual verification

**Step 1: Add color palette to toolbar**
```python
Div(
    *[Button("", style=f"background:{c}", data_on_click=f"$stroke_color = '{c}'", cls="color-btn")
      for c in ["#000", "#fff", "#f00", "#ff0", "#0f0", "#0ff", "#00f", "#f0f"]],
    cls="color-palette"
)
```

**Step 2: Implement custom color input**
- Add color input element
- Bind to $stroke_color signal

---

### Task 13: Stroke Width Control

**Files:**
- Modify: `stardeck/presenter.py`
- Modify: `stardeck/static/drawing.js`
- Test: Manual verification

**Step 1: Add width selector to toolbar**
```python
Div(
    *[Button(f"{'━' * i}", data_on_click=f"$stroke_width = {i*2}", cls="width-btn")
      for i in [1, 2, 3, 4, 5]],
    cls="width-selector"
)
```

**Step 2: Bind stroke width to drawing operations**

---

### Task 14: Undo/Redo System

**Files:**
- Modify: `stardeck/drawing.py`
- Modify: `stardeck/server.py`
- Test: `tests/test_drawing.py`

**Step 1: Write failing test**
```python
def test_drawing_state_undo():
    state = DrawingState()
    el1 = PenElement(id="el-1", ...)
    el2 = PenElement(id="el-2", ...)
    state.add_element(el1)
    state.add_element(el2)

    state.undo()
    assert len(state.elements[0]) == 1
    assert len(state.redo_stack) == 1

    state.redo()
    assert len(state.elements[0]) == 2
```

**Step 2: Implement**
```python
def undo(self):
    if not self.undo_stack:
        return None
    action = self.undo_stack.pop()
    self.redo_stack.append(action)
    # Reverse the action
    if action["type"] == "add":
        self._remove_element(action["element"].id)
    return action

def redo(self):
    if not self.redo_stack:
        return None
    action = self.redo_stack.pop()
    self.undo_stack.append(action)
    # Replay the action
    if action["type"] == "add":
        self._add_element(action["element"])
    return action
```

**Step 3: Add endpoints**
```python
@rt("/api/presenter/draw/undo")
@rt("/api/presenter/draw/redo")
```

---

### Task 15: Clear Slide Functionality

**Files:**
- Modify: `stardeck/drawing.py`
- Modify: `stardeck/server.py`
- Test: `tests/test_drawing.py`

**Step 1: Write failing test**
```python
def test_drawing_state_clear_slide():
    state = DrawingState()
    state.add_element(PenElement(id="el-1", slide_index=0, ...))
    state.add_element(PenElement(id="el-2", slide_index=0, ...))
    state.add_element(PenElement(id="el-3", slide_index=1, ...))

    state.clear_slide(0)

    assert len(state.elements.get(0, [])) == 0
    assert len(state.elements.get(1, [])) == 1  # Slide 1 unaffected
```

**Step 2: Implement endpoint**
```python
@rt("/api/presenter/draw/clear")
@sse
async def presenter_draw_clear(token: str, slide_index: int):
    pres = deck_state["presentation"]
    pres.drawing.clear_slide(slide_index)
    await pres.broadcast_drawing_clear(slide_index)
```

---

### Task 16: Keyboard Shortcuts

**Files:**
- Modify: `stardeck/presenter.py`
- Test: Manual verification

**Step 1: Add keyboard handler**
```python
Span(
    data_on_keydown=(
        """
        if (evt.key === 'd') { $drawing_mode = !$drawing_mode; }
        else if (evt.key === 'p') { $drawing_tool = 'pen'; }
        else if (evt.key === 'l') { $drawing_tool = 'line'; }
        else if (evt.key === 'r') { $drawing_tool = 'rect'; }
        else if (evt.key === 'o') { $drawing_tool = 'ellipse'; }
        else if (evt.key === 'a') { $drawing_tool = 'arrow'; }
        else if (evt.key === 'Escape') { $drawing_mode = false; }
        else if (evt.ctrlKey && evt.key === 'z') {
            evt.preventDefault();
            @post('/api/presenter/draw/undo');
        }
        """,
        {"window": True}
    ),
    style="display: none",
)
```

---

## Phase 2: Advanced Tools

### Task 17: Selection Tool

**Files:**
- Modify: `stardeck/static/drawing.js`
- Test: Manual verification

**Step 1: Implement hit testing**
```javascript
function hitTest(x, y, elements) {
    // Check each element's bounding box
    for (const el of elements.reverse()) {
        if (isPointInElement(x, y, el)) {
            return el;
        }
    }
    return null;
}
```

**Step 2: Show selection handles**
- Bounding box with corner/edge handles
- Highlight selected element

---

### Task 18: Move Elements

**Files:**
- Modify: `stardeck/static/drawing.js`
- Modify: `stardeck/server.py`
- Test: `tests/test_drawing.py`

**Step 1: Write failing test**
```python
def test_update_element_position():
    state = DrawingState()
    el = ShapeElement(id="el-1", x=10, y=10, width=50, height=50, ...)
    state.add_element(el)

    state.update_element("el-1", {"x": 20, "y": 30})

    assert state.elements[0][0].x == 20
    assert state.elements[0][0].y == 30
```

**Step 2: Implement drag-to-move**
- Capture drag start position
- Calculate delta on move
- Update element position
- Broadcast update

---

### Task 19: Resize Elements

**Files:**
- Modify: `stardeck/static/drawing.js`
- Test: Manual verification

**Step 1: Implement resize handles**
- 8 handles: 4 corners + 4 edges
- Drag corner to resize proportionally (with Shift)
- Drag edge to resize one dimension

**Step 2: Update element dimensions**
- Recalculate width/height based on handle drag
- Broadcast update

---

### Task 20: Delete Elements

**Files:**
- Modify: `stardeck/static/drawing.js`
- Modify: `stardeck/server.py`
- Test: `tests/test_drawing.py`

**Step 1: Write failing test**
```python
def test_delete_element():
    state = DrawingState()
    state.add_element(PenElement(id="el-1", ...))

    state.delete_element("el-1")

    assert len(state.elements.get(0, [])) == 0
    assert len(state.undo_stack) == 1  # Deletion is undoable
```

**Step 2: Implement**
- Delete key removes selected elements
- Add to undo stack for restoration
- Broadcast deletion

---

### Task 21: Text Tool

**Files:**
- Modify: `stardeck/static/drawing.js`
- Modify: `stardeck/drawing.py`
- Test: `tests/test_drawing.py`

**Step 1: Write failing test**
```python
def test_text_element_to_svg():
    element = TextElement(
        id="text-1",
        type="text",
        x=50, y=50,
        text="Hello World",
        font_size=16,
        font_family="sans-serif",
        stroke_color="#000",
        slide_index=0,
    )
    svg = element_to_svg(element)
    assert '<text' in svg
    assert 'Hello World' in svg
```

**Step 2: Implement**
- Click to place text cursor
- Show text input overlay
- On confirm, create TextElement
- Render as SVG `<text>`

---

### Task 22: Diamond Tool

**Files:**
- Modify: `stardeck/static/drawing.js`
- Modify: `stardeck/drawing.py`
- Test: `tests/test_drawing.py`

**Step 1: Write failing test**
```python
def test_diamond_element_to_svg():
    element = ShapeElement(
        id="diamond-1",
        type="diamond",
        x=50, y=50, width=40, height=40,
        stroke_color="#000",
        slide_index=0,
    )
    svg = element_to_svg(element)
    assert '<polygon' in svg or '<path' in svg
```

**Step 2: Implement**
- Same interaction as rectangle
- Render as rotated square (polygon with 4 points)

---

### Task 23: Highlighter Tool

**Files:**
- Modify: `stardeck/static/drawing.js`
- Test: Manual verification

**Step 1: Implement**
- Same as pen tool but:
  - Fixed semi-transparent yellow color (or configurable)
  - Larger default stroke width
  - Blend mode: multiply (for highlight effect)

```css
.highlighter-stroke {
    mix-blend-mode: multiply;
    opacity: 0.4;
}
```

---

### Task 24: Eraser Tool

**Files:**
- Modify: `stardeck/static/drawing.js`
- Test: Manual verification

**Step 1: Implement**
- Click on element to delete it
- Or: drag to delete elements touched by eraser path
- Uses hit testing from selection tool

---

### Task 25: Fill Color Support

**Files:**
- Modify: `stardeck/static/drawing.js`
- Modify: `stardeck/presenter.py`
- Test: `tests/test_drawing.py`

**Step 1: Add fill color picker to toolbar**
- Separate from stroke color
- "No fill" option (transparent)

**Step 2: Apply to shapes**
```python
def shape_to_svg(element):
    fill = element.fill_color or "none"
    return f'<rect ... fill="{fill}" />'
```

---

### Task 26: Opacity Control

**Files:**
- Modify: `stardeck/presenter.py`
- Modify: `stardeck/static/drawing.js`
- Test: Manual verification

**Step 1: Add opacity slider to toolbar**
```python
Input(type="range", min=0, max=100, value=100,
      data_model="opacity", cls="opacity-slider")
```

**Step 2: Apply to elements**
```javascript
element.style.opacity = opacity / 100;
```

---

## Phase 3: Audience Local Notes

### Task 27: Audience Local Notes Layer

**Files:**
- Modify: `stardeck/server.py`
- Modify: `stardeck/static/drawing.js`
- Test: Manual verification

**Step 1: Add second SVG layer for local notes**
```
┌─────────────────────────────┐
│   Local Notes Layer (top)   │  ← Editable by audience
├─────────────────────────────┤
│   Presenter Layer (middle)  │  ← Read-only, from SSE
├─────────────────────────────┤
│   Slide Content (bottom)    │
└─────────────────────────────┘
```

**Step 2: Separate drawing logic**
- Presenter draws → broadcast
- Audience draws → local layer only

---

### Task 28: localStorage Persistence

**Files:**
- Modify: `stardeck/static/drawing.js`
- Test: Manual verification

**Step 1: Implement save/load**
```javascript
function saveLocalNotes(slideIndex, elements) {
    const key = `stardeck_notes_slide_${slideIndex}`;
    localStorage.setItem(key, JSON.stringify(elements));
}

function loadLocalNotes(slideIndex) {
    const key = `stardeck_notes_slide_${slideIndex}`;
    const data = localStorage.getItem(key);
    return data ? JSON.parse(data) : [];
}
```

**Step 2: Auto-save on changes**
- Debounce saves (500ms)
- Load on slide change

---

### Task 29: My Notes Toggle UI

**Files:**
- Modify: `stardeck/server.py` (audience view)
- Test: Manual verification

**Step 1: Add toggle button for audience**
```python
Button(
    "📝 My Notes",
    data_on_click="$local_notes_mode = !$local_notes_mode",
    data_class_active="$local_notes_mode",
    cls="notes-toggle"
)
```

**Step 2: Show/hide local toolbar based on mode**

---

### Task 30: Export Drawings

**Files:**
- Modify: `stardeck/static/drawing.js`
- Test: Manual verification

**Step 1: Implement SVG export**
```javascript
function exportAsSVG(elements) {
    const svg = elementsToSVG(elements);
    const blob = new Blob([svg], {type: 'image/svg+xml'});
    downloadBlob(blob, 'slide-notes.svg');
}
```

**Step 2: Implement PNG export**
```javascript
function exportAsPNG(svgElement) {
    // Convert SVG to canvas, then to PNG
    const canvas = document.createElement('canvas');
    // ... render SVG to canvas ...
    canvas.toBlob(blob => downloadBlob(blob, 'slide-notes.png'));
}
```

---

## Commit Convention

After each task:
```bash
git commit -am "feat(drawing): <task description>"
```

Examples:
- `feat(drawing): add drawing data models`
- `feat(drawing): implement pen tool with SVG paths`
- `feat(drawing): add undo/redo system`
