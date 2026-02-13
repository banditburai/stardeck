# Drawing & Annotations Design

**Created:** 2026-02-02
**Status:** Draft

## Problem Statement

Presenters need to annotate slides in real-time during presentations - circling items, drawing arrows, highlighting sections. These annotations should appear on audience screens instantly. Additionally, audience members want to make personal annotations on their own view for note-taking without affecting others.

## Solution Overview

Add an Excalidraw-style drawing layer over slides with full whiteboard functionality: freehand drawing, shapes, text boxes, arrows, and selection/manipulation tools. Leverage existing broadcast sync for presenter→audience updates. Support local-only drawing mode for audience personal annotations.

## Feature Comparison

| Feature | Slidev | Excalidraw | StarDeck Target |
|---------|--------|------------|-----------------|
| Freehand pen | Yes | Yes | Yes |
| Line tool | Yes | Yes | Yes |
| Rectangle | Yes | Yes | Yes |
| Ellipse | Yes | Yes | Yes |
| Diamond | No | Yes | Yes |
| Arrow | No | Yes | Yes |
| Text boxes | No | Yes | Yes |
| Selection tool | No | Yes | Yes |
| Move/resize objects | No | Yes | Yes |
| Highlighter | Yes | No | Yes |
| Eraser | Yes | Yes | Yes |
| Color picker | Yes | Yes | Yes |
| Brush sizes | Yes | Yes | Yes |
| Fill color | No | Yes | Yes |
| Undo/Redo | Yes | Yes | Yes |
| Clear all | Yes | Yes | Yes |
| Real-time sync | Yes | Yes (collab) | Yes |
| Presenter-only broadcast | Yes | N/A | Yes |
| **Audience local drawing** | No | N/A | **Yes** |
| Hand-drawn style | No | Yes | Phase 2 |
| Persistence to file | Yes | Yes | Yes |
| Stylus/tablet support | Yes | Yes | Yes |
| Pressure sensitivity | Yes | No | Phase 2 |

## Two Drawing Modes

### 1. Presenter Broadcast Mode
- Presenter draws → broadcasts to all audience clients
- Full toolbar with all tools
- Server stores drawing state
- Audience sees presenter's drawings in real-time

### 2. Audience Local Mode
- Audience draws → local only, no network traffic
- Same tools available
- Stored in browser localStorage per slide
- Personal annotations for note-taking
- Toggle: "My Notes" mode

## Architecture

### Drawing Layer Structure

```
┌─────────────────────────────────────┐
│    Local Annotations Layer          │  ← Audience personal notes (localStorage)
├─────────────────────────────────────┤
│    Presenter Drawing Layer          │  ← Broadcast from presenter (SSE)
├─────────────────────────────────────┤
│         Slide Content               │  ← Existing slide rendering
└─────────────────────────────────────┘
```

### Data Model (Excalidraw-style Objects)

```python
@dataclass
class DrawingElement:
    """Base class for all drawable elements."""
    id: str                    # Unique identifier (uuid)
    type: str                  # "pen" | "line" | "rect" | "ellipse" | "diamond" | "arrow" | "text"
    x: float                   # Top-left X (0-100 percentage)
    y: float                   # Top-left Y (0-100 percentage)
    width: float               # Bounding box width
    height: float              # Bounding box height
    stroke_color: str          # Stroke color "#ff0000"
    stroke_width: int          # Stroke width in pixels
    fill_color: str | None     # Fill color (None = transparent)
    opacity: float             # 0-1
    rotation: float            # Degrees
    locked: bool               # Prevent modification
    slide_index: int           # Which slide
    z_index: int               # Stacking order
    created_at: float          # Timestamp

@dataclass
class PenElement(DrawingElement):
    """Freehand drawing path."""
    points: list[Point]        # Path points [(x,y,pressure), ...]

@dataclass
class ShapeElement(DrawingElement):
    """Rectangle, ellipse, diamond."""
    # Uses x, y, width, height from base class

@dataclass
class LineElement(DrawingElement):
    """Line or arrow."""
    points: list[Point]        # Start and end points
    start_arrow: bool          # Arrow at start
    end_arrow: bool            # Arrow at end

@dataclass
class TextElement(DrawingElement):
    """Text box."""
    text: str                  # The text content
    font_size: int             # Font size
    font_family: str           # Font family
    text_align: str            # "left" | "center" | "right"

@dataclass
class Point:
    x: float                   # 0-100 percentage
    y: float                   # 0-100 percentage
    pressure: float = 1.0      # 0-1 for stylus

@dataclass
class DrawingState:
    """Server-side state for presenter drawings."""
    elements: dict[int, list[DrawingElement]]  # slide_index -> elements
    undo_stack: list[DrawingElement]
    redo_stack: list[DrawingElement]
    selected_ids: list[str]    # Currently selected element IDs
```

### Coordinate System

Use **percentage-based coordinates** (0-100) for viewport independence:
- Drawings scale correctly across different screen sizes
- Serialization is resolution-agnostic
- Sync works regardless of audience viewport size

### Sync Protocol

Extend existing SSE broadcast:

```
event: datastar-patch-signals
data: signals {"drawing_strokes": [...], "drawing_tool": "pen", ...}

event: datastar-drawing-stroke
data: stroke {"id": "s1", "tool": "pen", "color": "#f00", "points": [...]}

event: datastar-drawing-clear
data: clear {"slide_index": 3}

event: datastar-drawing-undo
data: undo {"stroke_id": "s1"}
```

## Implementation Approach

### Option A: SVG-Based (like drauu)
**Pros:** Scalable, serializable, familiar pattern
**Cons:** Complex path manipulation, harder real-time streaming

### Option B: Canvas-Based with SVG Export
**Pros:** Fast real-time drawing, simpler point capture
**Cons:** Need to convert to SVG for persistence

### Option C: Hybrid - Canvas for Drawing, SVG for Rendering
**Pros:** Best of both - fast capture, clean rendering
**Cons:** Two rendering systems to maintain

**Recommendation:** Option A (SVG-Based)
- Matches Slidev's approach
- Strokes are naturally serializable as path data
- Scales perfectly to any viewport
- Can save drawings directly as SVG files

### Client-Side Components

```
stardeck/
├── static/
│   └── drawing.js           # Drawing layer JS module
└── themes/
    └── default/
        └── styles.css       # Drawing toolbar CSS

Server:
├── server.py                # Add drawing endpoints
└── models.py                # Add Stroke, DrawingState models
```

### Drawing Toolbar UI

```
┌────────────────────────────────────────────────────────────────────────┐
│ Tools:                                                                  │
│ [🔘 Select] [✏️ Pen] [🖍️ Highlight] [📏 Line] [➡️ Arrow]               │
│ [⬜ Rect] [⭕ Ellipse] [◇ Diamond] [T Text] [🧹 Eraser]                 │
├────────────────────────────────────────────────────────────────────────┤
│ Style:                                                                  │
│ [Stroke: ■■■] [Fill: □□□] [Size: ━━━] [Opacity: ▓▓░]                  │
├────────────────────────────────────────────────────────────────────────┤
│ Actions:                                                                │
│ [↩️ Undo] [↪️ Redo] [🗑️ Delete] [📋 Clear Slide]                        │
│ [📝 My Notes: OFF] ← Toggle local/broadcast mode (audience only)       │
└────────────────────────────────────────────────────────────────────────┘
```

**Presenter toolbar:** Full tools, always broadcasts
**Audience toolbar:** Same tools, "My Notes" toggle for local-only mode (default ON)

### Color Palette

Quick colors: Black, White, Red, Orange, Yellow, Green, Blue, Purple
Custom: Color picker for any hex value

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `d` | Toggle drawing mode on/off |
| `v` | Selection tool |
| `p` | Pen tool |
| `h` | Highlighter tool |
| `l` | Line tool |
| `a` | Arrow tool |
| `r` | Rectangle tool |
| `o` | Ellipse (oval) tool |
| `m` | Diamond tool |
| `t` | Text tool |
| `e` | Eraser tool |
| `Delete/Backspace` | Delete selected |
| `Ctrl+A` | Select all on slide |
| `Ctrl+Z` | Undo |
| `Ctrl+Shift+Z` / `Ctrl+Y` | Redo |
| `Ctrl+C` | Copy selected |
| `Ctrl+V` | Paste |
| `Ctrl+D` | Duplicate selected |
| `[` / `]` | Decrease/Increase brush size |
| `1-9` | Stroke color presets |
| `Shift+1-9` | Fill color presets |
| `Esc` | Exit drawing mode / Deselect |

### Selection Tool Features

When elements are selected:
- **Bounding box** with resize handles (corners + edges)
- **Rotation handle** at top
- **Drag to move** elements
- **Multi-select** with Shift+Click or drag rectangle
- **Delete** with Delete/Backspace key

## Data Flow

### Presenter Drawing (Broadcast to Audience)

```
1. Presenter creates/modifies element on canvas
2. Element data captured (type, position, style, etc.)
3. POST /api/presenter/draw with element data
4. Server adds to DrawingState.elements[slide_index]
5. Server broadcasts via /api/events SSE
6. Audience clients receive and render element
```

### Audience Local Drawing (No Broadcast)

```
1. Audience member toggles "My Notes" mode ON
2. Draws element on local canvas layer
3. Element stored in localStorage: stardeck_notes_slide_{N}
4. No network traffic - purely client-side
5. Persists across browser sessions
6. Displayed above presenter drawings layer
```

### Selection & Manipulation (Presenter)

```
1. Presenter clicks element or drag-selects multiple
2. POST /api/presenter/draw/select with element IDs
3. Server broadcasts selection state (for cursor visibility)
4. Presenter drags/resizes → POST /api/presenter/draw/update
5. Server updates element, broadcasts change
6. Audience sees manipulation in real-time
```

### Undo/Redo (Presenter)

```
1. Presenter presses Ctrl+Z
2. POST /api/presenter/draw/undo
3. Server moves last action to redo_stack
4. Server broadcasts undo event with affected elements
5. Audience clients revert element state
```

### Clear Slide (Presenter)

```
1. Presenter clicks Clear Slide
2. POST /api/presenter/draw/clear?slide_index=N
3. Server clears elements for slide, resets undo/redo
4. Server broadcasts clear event
5. Audience clients clear presenter drawing layer
   (Local notes layer unaffected)
```

## Configuration

Frontmatter options (per deck):

```yaml
---
drawing:
  enabled: true           # Enable drawing (default: true)
  presenterOnly: true     # Only presenter can draw (default: true)
  persist: false          # Save drawings to .stardeck/drawings/ (default: false)
  syncAll: false          # Sync all clients' drawings (default: false, presenter only)
---
```

## Persistence

When `persist: true`:
- Save drawings as SVG files: `.stardeck/drawings/slide-{N}.svg`
- Load on deck start
- Auto-save on change (debounced)

SVG format:
```svg
<svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg">
  <path d="M10,20 L30,40 L50,30" stroke="#ff0000" stroke-width="2" fill="none"/>
  <ellipse cx="60" cy="50" rx="20" ry="15" stroke="#00ff00" stroke-width="1" fill="none"/>
</svg>
```

## Audience View

Audience sees two layers:

### 1. Presenter Drawings Layer (Read-Only)
- Receives presenter drawings via SSE
- Rendered below local notes
- Cannot be edited by audience

### 2. Local Notes Layer (Editable)
- Toggle with "My Notes" button or `n` key
- Full drawing toolbar available
- Stored in localStorage per slide
- Persists across sessions
- Private to each audience member
- Export option: download as PNG/SVG

## Technical Considerations

### SVG Path Generation

Freehand strokes use SVG path with quadratic curves for smoothness:
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

### Pointer Events

Drawing mode toggles pointer-events on canvas:
- Drawing mode ON: `pointer-events: auto` on canvas
- Drawing mode OFF: `pointer-events: none` (clicks pass through to slides)

### Touch/Stylus Detection

```javascript
element.addEventListener('pointerdown', (e) => {
  const isStylus = e.pointerType === 'pen';
  const pressure = e.pressure || 0.5;
  // Stylus auto-enables drawing without toggle
});
```

## Open Questions

1. ~~Shape preview while drawing?~~ **Yes** - ghost shape while dragging
2. **Per-slide or global undo?** → Per-slide (simpler, matches slide context)
3. **Maximum elements limit?** → 500 per slide? Warn at 400?
4. **Drawing on click-reveal elements?** → Yes, drawings are separate layer
5. **Copy/paste across slides?** → Yes, useful for repeated annotations
6. **Z-order controls?** → Bring to front/send to back? (Phase 2)
7. **Grouping elements?** → Phase 2 feature

## Key Decisions

1. **SVG over Canvas** - Better for serialization, scaling, and selection
2. **Percentage coordinates** - Viewport independence across devices
3. **Two-layer architecture** - Presenter broadcast + audience local
4. **Existing SSE for sync** - No new infrastructure needed
5. **localStorage for audience notes** - No server storage needed
6. **Excalidraw-style tools** - Full whiteboard functionality
7. **Selection-first design** - Objects can be modified after creation

## Implementation Phases

### Phase 1: Core Drawing (MVP)
- Drawing layer (SVG overlay)
- Tools: Pen, Line, Rectangle, Ellipse, Arrow
- Colors and stroke width
- Undo/Redo
- Clear slide
- Presenter → Audience broadcast sync
- Basic keyboard shortcuts

### Phase 2: Advanced Tools
- Selection tool (move, resize, delete)
- Text boxes
- Diamond shape
- Highlighter tool
- Eraser tool
- Fill colors
- Opacity control

### Phase 3: Audience Local Notes
- "My Notes" toggle for audience
- localStorage persistence
- Separate rendering layer
- Export to PNG/SVG

### Phase 4: Polish
- Rotation handles
- Copy/paste/duplicate
- Multi-select
- Stylus pressure sensitivity
- Hand-drawn style option
- Z-order controls
- Grouping

## Next Steps

→ Create implementation plan with write-plan-with-beads

## Sources

- [Slidev Drawing & Annotations](https://sli.dev/features/drawing.html)
- [drauu library](https://github.com/antfu/drauu)
- [Excalidraw](https://excalidraw.com/) - Inspiration for full whiteboard functionality
