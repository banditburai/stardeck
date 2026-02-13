# StarHTML Drawing Plugin Design

**Created:** 2026-02-02
**Status:** Draft
**Parent:** [Drawing & Annotations Design](./2026-02-02-drawing-annotations.md)

This document describes the design of a general-purpose drawing plugin for StarHTML, with stardeck (presentation annotations) as the primary use case.

---

## Plugin Architecture

This section specifies the **Core Plugin Architecture & Signals** following established patterns from existing StarHTML plugins (canvas, drag, motion, scroll, split).

### Pattern Analysis from Existing Plugins

| Plugin | Signals | Methods | Actions | Config | Critical CSS |
|--------|---------|---------|---------|--------|--------------|
| **canvas** | pan_x, pan_y, zoom, context_menu_* | reset_view, zoom_in, zoom_out | No | Yes (via setConfig) | No |
| **drag** | is_dragging, element_id, x, y, drop_zone | No | No | Yes (via setConfig) | Yes |
| **motion** | No | No | animate, sequence, set, pause, play, stop, cancel, remove, replace | No | Yes |
| **scroll** | x, y, direction, page_progress, is_top, is_bottom, visible_percent, progress | No | No | No | No |
| **split** | position, sizes, is_dragging, direction, collapsed | No | No | Yes (via setConfig) | No |
| **persist** | No | No | No | No | Yes |

**Key Observations:**
1. **Signals** are named with a configurable prefix (`{signal}_property`)
2. **Methods** are exposed via `window.__{signal}.methodName()`
3. **Actions** use `@plugin('operation', args)` syntax
4. **Config** is passed via `setConfig()` and stored on `window.__starhtml_{plugin}_config`
5. **Critical CSS** prevents flash of unstyled/unprocessed content
6. **argNames** array lists all signal names for Datastar registration

### Signal Prefix

The drawing plugin uses a configurable signal prefix (default: `"drawing"`):

```python
drawing = Plugin("drawing", name="drawing")  # Creates $drawing_* signals
my_canvas = drawing(name="annotations")       # Creates $annotations_* signals
```

### Signals

The plugin exposes the following reactive signals:

```typescript
// Core state signals
`${signal}_mode`: "off" | "draw" | "select" | "pan"  // Current interaction mode
`${signal}_tool`: Tool                                // Active drawing tool
`${signal}_is_drawing`: boolean                       // Currently drawing a stroke/shape
`${signal}_is_selecting`: boolean                     // Currently making a selection
`${signal}_can_undo`: boolean                         // Undo stack has items
`${signal}_can_redo`: boolean                         // Redo stack has items

// Active stroke/shape preview
`${signal}_preview_type`: Tool | null                 // Type of element being drawn
`${signal}_preview_x`: number                         // Preview bounding box X (%)
`${signal}_preview_y`: number                         // Preview bounding box Y (%)
`${signal}_preview_width`: number                     // Preview width (%)
`${signal}_preview_height`: number                    // Preview height (%)

// Style signals (two-way bound to toolbar)
`${signal}_stroke_color`: string                      // Current stroke color (#hex)
`${signal}_fill_color`: string | null                 // Current fill color (null = none)
`${signal}_stroke_width`: number                      // Stroke width in pixels (1-20)
`${signal}_opacity`: number                           // Element opacity (0-1)

// Selection state
`${signal}_selected_ids`: string[]                    // IDs of selected elements
`${signal}_selection_count`: number                   // Number of selected elements
`${signal}_selection_bounds`: BoundingBox | null      // Bounding box of selection

// Layer control (for audience mode)
`${signal}_layer`: "presenter" | "local"              // Which layer is active
`${signal}_local_visible`: boolean                    // Show local annotations layer
`${signal}_presenter_visible`: boolean                // Show presenter drawings layer

// Element count (for performance warnings)
`${signal}_element_count`: number                     // Total elements on current slide

// Pointer position (for cursor display)
`${signal}_pointer_x`: number                         // Current pointer X (%)
`${signal}_pointer_y`: number                         // Current pointer Y (%)
```

**Tool Types:**

```typescript
type Tool =
  | "select"      // Selection/manipulation tool
  | "pen"         // Freehand drawing
  | "highlighter" // Transparent highlighter pen
  | "line"        // Straight line
  | "arrow"       // Line with arrowhead
  | "rect"        // Rectangle
  | "ellipse"     // Ellipse/circle
  | "diamond"     // Diamond shape
  | "text"        // Text box
  | "eraser"      // Eraser tool
```

**Python Plugin Definition:**

```python
drawing = Plugin(
    "drawing",
    signals=(
        # Core state
        "mode",
        "tool",
        "is_drawing",
        "is_selecting",
        "can_undo",
        "can_redo",
        # Preview
        "preview_type",
        "preview_x",
        "preview_y",
        "preview_width",
        "preview_height",
        # Style
        "stroke_color",
        "fill_color",
        "stroke_width",
        "opacity",
        # Selection
        "selected_ids",
        "selection_count",
        "selection_bounds",
        # Layers
        "layer",
        "local_visible",
        "presenter_visible",
        # Stats
        "element_count",
        # Pointer
        "pointer_x",
        "pointer_y",
    ),
    methods=(
        "clear",
        "undo",
        "redo",
        "delete_selected",
        "select_all",
        "deselect",
        "set_tool",
        "set_style",
        "export_svg",
        "import_svg",
        "toggle_mode",
    ),
    actions=(
        "start",
        "commit",
        "cancel",
        "add_element",
        "update_element",
        "remove_element",
        "select",
        "transform",
    ),
    critical_css="[data-drawing]:not([data-drawing-ready]){pointer-events:none}[data-drawing-layer]{position:absolute;inset:0;pointer-events:none}[data-drawing-mode='draw'] [data-drawing-layer],[data-drawing-mode='select'] [data-drawing-layer]{pointer-events:auto}",
)
```

### Methods

Methods are exposed via `window.__{signal}` for imperative control:

```typescript
interface DrawingMethods {
  // Canvas operations
  clear(): void                              // Clear all elements on current slide
  undo(): void                               // Undo last action
  redo(): void                               // Redo last undone action

  // Selection operations
  deleteSelected(): void                     // Delete selected elements
  selectAll(): void                          // Select all elements on current slide
  deselect(): void                           // Clear selection

  // Tool/style control
  setTool(tool: Tool): void                  // Switch active tool
  setStyle(style: Partial<StyleOptions>): void  // Update style options

  // Mode control
  toggleMode(): void                         // Toggle drawing mode on/off

  // Import/export
  exportSvg(): string                        // Export current slide as SVG
  importSvg(svg: string): void               // Import SVG elements
}
```

**Python Access Pattern:**

```python
from starhtml.plugins import drawing

# In a template
Button("Clear All", data_on_click=drawing.clear)
Button("Undo", data_on_click=drawing.undo, data_attr_disabled=~drawing.can_undo)
Button("Select Pen", data_on_click=drawing.set_tool("pen"))
```

**Generated JavaScript:**

```javascript
// drawing.clear → window.__drawing.clear()
// drawing.undo → window.__drawing.undo()
// drawing.set_tool("pen") → window.__drawing.setTool('pen')
```

### Actions

Actions use the Datastar action pattern for event-driven drawing operations:

```typescript
interface DrawingActions {
  // Drawing lifecycle
  start(tool: Tool, point: Point, style?: StyleOptions): void
  commit(): void
  cancel(): void

  // Element CRUD
  addElement(element: DrawingElement): string  // Returns element ID
  updateElement(id: string, updates: Partial<DrawingElement>): void
  removeElement(id: string): void

  // Selection
  select(ids: string | string[], additive?: boolean): void

  // Transform
  transform(ids: string[], transform: Transform): void
}
```

**Usage Examples:**

```html
<!-- Start drawing on pointer down -->
<svg data-on-pointerdown="@drawing('start', $drawing_tool, {x: evt.offsetX, y: evt.offsetY})">

<!-- Commit stroke on pointer up -->
<svg data-on-pointerup="@drawing('commit')">

<!-- Cancel with Escape key -->
<div data-on-keydown__window="evt.key === 'Escape' && @drawing('cancel')">

<!-- Add a predefined shape -->
<button data-on-click="@drawing('addElement', {type: 'rect', x: 10, y: 10, width: 20, height: 20})">
  Add Rectangle
</button>

<!-- Select element by ID -->
<g data-on-click="@drawing('select', 'element-123')">

<!-- Multi-select with shift -->
<g data-on-click="@drawing('select', 'element-456', evt.shiftKey)">

<!-- Transform selected elements -->
<button data-on-click="@drawing('transform', $drawing_selected_ids, {translate: {x: 10, y: 0}})">
  Move Right
</button>
```

### Configuration

Configuration is passed via `setConfig()` and stored globally:

```typescript
interface DrawingConfig {
  // Core settings
  signal: string                    // Signal prefix (default: "drawing")
  slideSelector: string             // CSS selector for slides (default: "[data-slide]")

  // Feature toggles
  tools: Tool[]                     // Enabled tools (default: all)
  enablePan: boolean                // Allow pan mode (default: true)
  enableZoom: boolean               // Allow zoom during drawing (default: false)

  // Style defaults
  defaultStrokeColor: string        // Default stroke color (default: "#000000")
  defaultFillColor: string | null   // Default fill color (default: null)
  defaultStrokeWidth: number        // Default stroke width (default: 2)
  defaultOpacity: number            // Default opacity (default: 1)

  // Color palette
  colorPalette: string[]            // Quick-access colors
  strokeWidths: number[]            // Available stroke widths

  // Coordinate system
  coordinateSystem: "percentage" | "absolute"  // (default: "percentage")

  // Performance
  maxElements: number               // Max elements per slide (default: 500)
  warnAtElements: number            // Warning threshold (default: 400)
  throttleMs: number                // Pointer event throttle (default: 8)

  // Layers (for StarDeck integration)
  enableLayers: boolean             // Enable presenter/local layers (default: false)
  defaultLayer: "presenter" | "local"  // (default: "presenter")

  // Callbacks
  onElementCreated?: (el: DrawingElement) => void
  onElementUpdated?: (el: DrawingElement) => void
  onElementDeleted?: (id: string) => void
  onStyleChanged?: (style: StyleOptions) => void

  // Persistence
  persistKey?: string               // localStorage key for local layer
  autosave: boolean                 // Auto-save local annotations (default: true)

  // Sync (for broadcast mode)
  broadcastUrl?: string             // SSE endpoint for broadcasting
  syncEnabled: boolean              // Enable broadcast sync (default: false)
}
```

**Python Configuration:**

```python
from starhtml.plugins import drawing

# Default configuration
drawing_plugin = drawing()

# Custom configuration
drawing_plugin = drawing(
    name="annotations",
    tools=["pen", "highlighter", "arrow", "rect"],
    default_stroke_color="#ff0000",
    color_palette=["#000", "#fff", "#f00", "#0f0", "#00f", "#ff0"],
    max_elements=300,
    enable_layers=True,  # For StarDeck
)

# In headers
from starhtml.plugins import plugins_hdrs
hdrs = plugins_hdrs(drawing_plugin)
```

### Critical CSS

The critical CSS prevents flash of unstyled content and ensures proper layering:

```css
/* Hide drawing layer until initialized */
[data-drawing]:not([data-drawing-ready]) {
  pointer-events: none;
}

/* Drawing layer positioning */
[data-drawing-layer] {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

/* Enable pointer events only in draw/select modes */
[data-drawing-mode="draw"] [data-drawing-layer],
[data-drawing-mode="select"] [data-drawing-layer] {
  pointer-events: auto;
}

/* Cursor styles per tool */
[data-drawing-mode="draw"][data-drawing-tool="pen"] {
  cursor: crosshair;
}

[data-drawing-mode="draw"][data-drawing-tool="eraser"] {
  cursor: url('eraser-cursor.svg') 8 8, crosshair;
}

[data-drawing-mode="select"] {
  cursor: default;
}

[data-drawing-mode="pan"] {
  cursor: grab;
}

/* Selection handles */
[data-drawing-handle] {
  fill: white;
  stroke: #3b82f6;
  stroke-width: 1;
  cursor: pointer;
}
```

### TypeScript Plugin Structure

```typescript
// drawing.ts - follows patterns from canvas.ts, drag.ts, motion.ts

import { effect, getPath, mergePatch } from "datastar";
import { createRAFThrottle } from "./throttle.js";
import type {
  ActionContext,
  ActionPlugin,
  AttributeContext,
  AttributePlugin,
  OnRemovalFn
} from "./types.js";

// ============================================================
// Signal Names Generator
// ============================================================

function getDrawingArgNames(signal = "drawing"): string[] {
  return [
    `${signal}_mode`, `${signal}_tool`, `${signal}_is_drawing`,
    `${signal}_is_selecting`, `${signal}_can_undo`, `${signal}_can_redo`,
    `${signal}_preview_type`, `${signal}_preview_x`, `${signal}_preview_y`,
    `${signal}_preview_width`, `${signal}_preview_height`,
    `${signal}_stroke_color`, `${signal}_fill_color`, `${signal}_stroke_width`,
    `${signal}_opacity`, `${signal}_selected_ids`, `${signal}_selection_count`,
    `${signal}_selection_bounds`, `${signal}_layer`, `${signal}_local_visible`,
    `${signal}_presenter_visible`, `${signal}_element_count`,
    `${signal}_pointer_x`, `${signal}_pointer_y`,
  ];
}

// ============================================================
// Attribute Plugin (registers with Datastar's attribute())
// ============================================================

const drawingAttributePlugin: AttributePlugin = {
  name: "drawing",
  requirement: { key: "allowed", value: "allowed" },

  apply(ctx: AttributeContext): OnRemovalFn | void {
    const globalConfig = window.__starhtml_drawing_config;
    const config = { ...DEFAULT_CONFIG, ...globalConfig };

    const controller = new DrawingController(ctx, config);

    return () => {
      controller.destroy();
    };
  },
};

// ============================================================
// Action Plugin (registers with Datastar's action())
// ============================================================

const drawingActionPlugin: ActionPlugin = {
  name: "drawing",

  apply: (ctx: ActionContext, operation: string, ...args: unknown[]): void => {
    const config = window.__starhtml_drawing_config || DEFAULT_CONFIG;
    const signal = config.signal || "drawing";
    const controller = controllerRegistry[signal];

    switch (operation) {
      case "start":
        controller?.startDrawing(...args);
        break;
      case "commit":
        controller?.commitElement();
        break;
      case "cancel":
        controller?.cancelElement();
        break;
      case "addElement":
        controller?.addElement(args[0]);
        break;
      // ... other operations
    }
  },
};

// ============================================================
// Controller Registry & Method Registration
// ============================================================

const controllerRegistry: Record<string, DrawingController | null> = {};

function registerDrawingMethods(signal: string) {
  const actionsKey = `__${signal}`;
  if ((window as any)[actionsKey]) return;

  (window as any)[actionsKey] = {
    clear: () => controllerRegistry[signal]?.clear(),
    undo: () => controllerRegistry[signal]?.undo(),
    redo: () => controllerRegistry[signal]?.redo(),
    deleteSelected: () => controllerRegistry[signal]?.deleteSelected(),
    selectAll: () => controllerRegistry[signal]?.selectAll(),
    deselect: () => controllerRegistry[signal]?.deselect(),
    setTool: (tool) => controllerRegistry[signal]?.setTool(tool),
    setStyle: (style) => controllerRegistry[signal]?.setStyle(style),
    toggleMode: () => controllerRegistry[signal]?.toggleMode(),
    exportSvg: () => controllerRegistry[signal]?.exportSvg(),
    importSvg: (svg) => controllerRegistry[signal]?.importSvg(svg),
  };
}

// ============================================================
// Plugin Export with setConfig
// ============================================================

const drawingPlugin = {
  ...drawingAttributePlugin,
  argNames: [] as string[],

  setConfig(config: Partial<DrawingConfig>) {
    window.__starhtml_drawing_config = { ...DEFAULT_CONFIG, ...config };
    const signal = config.signal || "drawing";
    this.argNames = getDrawingArgNames(signal);
    registerDrawingMethods(signal);
  },
};

export default drawingPlugin;
export { drawingActionPlugin };
```

### Integration with Datastar's Reactive System

**Signal Updates:**

```typescript
import { mergePatch } from "datastar";

// Update multiple signals atomically
mergePatch({
  [`${signal}_is_drawing`]: true,
  [`${signal}_tool`]: "pen",
  [`${signal}_stroke_color`]: "#ff0000",
});
```

**Effect-Based Reactivity:**

```typescript
import { effect, getPath } from "datastar";

// React to tool changes
const cleanup = effect(() => {
  const currentTool = getPath(`${signal}_tool`);
  updateCursor(currentTool);
});
```

**Two-Way Binding in Templates:**

```html
<!-- Color picker bound to stroke_color signal -->
<input type="color" data-model="drawing_stroke_color">

<!-- Stroke width slider -->
<input type="range" min="1" max="20" data-model="drawing_stroke_width">

<!-- Tool buttons -->
<button data-on-click="$drawing_tool = 'pen'"
        data-class-active="$drawing_tool === 'pen'">
  Pen
</button>

<!-- Undo button with disabled state -->
<button data-on-click="window.__drawing.undo()"
        data-attr-disabled="!$drawing_can_undo">
  Undo
</button>
```

---

## Integration Patterns

### Server Communication

The drawing plugin communicates with the server through a callback-based API that applications implement. This decouples the plugin from any specific transport layer.

#### Callback Interface

```javascript
// Application provides these callbacks when initializing the plugin
const drawingCallbacks = {
  // Called when a stroke/element is completed (mouse up / touch end)
  onStrokeComplete: async (element) => {
    // Application handles sending to server
    await fetch('/api/draw', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(element)
    });
  },

  // Called when user requests undo
  onUndo: async () => {
    const response = await fetch('/api/draw/undo', { method: 'POST' });
    return response.json(); // Returns { undone: true, element_id: "..." }
  },

  // Called when user requests redo
  onRedo: async () => {
    const response = await fetch('/api/draw/redo', { method: 'POST' });
    return response.json();
  },

  // Called when user clears the canvas
  onClear: async (layerId) => {
    await fetch(`/api/draw/clear?layer=${layerId}`, { method: 'POST' });
  },

  // Called when an element is modified (moved, resized, deleted)
  onElementUpdate: async (elementId, changes) => {
    await fetch(`/api/draw/update/${elementId}`, {
      method: 'PATCH',
      body: JSON.stringify(changes)
    });
  },

  // Called when element is deleted
  onElementDelete: async (elementId) => {
    await fetch(`/api/draw/delete/${elementId}`, { method: 'DELETE' });
  }
};

// Initialize the drawing plugin
const drawing = new DrawingLayer(container, {
  callbacks: drawingCallbacks,
  mode: 'broadcast',  // or 'local'
  tools: ['pen', 'line', 'rect', 'ellipse', 'arrow', 'text'],
  defaultColor: '#ff0000',
  defaultStrokeWidth: 2
});
```

#### Element Data Format

All elements use percentage-based coordinates (0-100) for viewport independence:

```typescript
interface DrawingElement {
  id: string;              // UUID
  type: 'pen' | 'line' | 'rect' | 'ellipse' | 'arrow' | 'text' | 'diamond';
  stroke_color: string;    // Hex color "#rrggbb"
  stroke_width: number;    // Pixels
  fill_color?: string;     // Optional fill
  opacity?: number;        // 0-1
  layer_id?: string;       // For multi-layer support
  z_index?: number;        // Stacking order
  created_by?: string;     // User ID for multi-user
  created_at?: number;     // Timestamp
}

interface PenElement extends DrawingElement {
  type: 'pen';
  points: Point[];         // Freehand path
}

interface LineElement extends DrawingElement {
  type: 'line' | 'arrow';
  points: [Point, Point];  // Start and end
  start_arrow?: boolean;
  end_arrow?: boolean;
}

interface ShapeElement extends DrawingElement {
  type: 'rect' | 'ellipse' | 'diamond';
  x: number;               // Top-left X (0-100)
  y: number;               // Top-left Y (0-100)
  width: number;           // Percentage width
  height: number;          // Percentage height
}

interface TextElement extends DrawingElement {
  type: 'text';
  x: number;
  y: number;
  text: string;
  font_size: number;
  font_family: string;
}

interface Point {
  x: number;               // 0-100 percentage
  y: number;               // 0-100 percentage
  pressure?: number;       // 0-1 for stylus support
}
```

### SSE Broadcast

For real-time sync (like presenter-to-audience), the plugin receives external updates via SSE. The application listens to SSE events and pushes updates to the plugin:

#### Server-Side Event Format (Stardeck Example)

```python
# In server.py - broadcasting drawing events
async def broadcast_drawing(self, element: DrawingElement):
    """Broadcast drawing element to all subscribers."""
    async with self._lock:
        for queue in self.subscribers:
            try:
                queue.put_nowait({
                    "type": "drawing",
                    "action": "add",      # add | remove | update | clear
                    "element": element_to_dict(element),
                })
            except asyncio.QueueFull:
                pass

# In event_stream - sending SSE events
if state.get("type") == "drawing":
    action = state.get("action", "add")
    if action == "add":
        event_data = json.dumps({"action": "add", "element": state["element"]})
    elif action == "remove":
        event_data = json.dumps({
            "action": "remove",
            "element_id": state["element_id"],
            "slide_index": state["slide_index"],
        })
    elif action == "clear":
        event_data = json.dumps({
            "action": "clear",
            "slide_index": state["slide_index"],
        })
    yield f"event: datastar-drawing\ndata: {event_data}\n\n"
```

#### Client-Side Event Handling

```javascript
// Application listens to SSE and updates the drawing layer
const eventSource = new EventSource('/api/events');

eventSource.addEventListener('datastar-drawing', (event) => {
  const data = JSON.parse(event.data);

  switch (data.action) {
    case 'add':
      drawing.addElement(data.element);
      break;
    case 'remove':
      drawing.removeElement(data.element_id);
      break;
    case 'update':
      drawing.updateElement(data.element_id, data.changes);
      break;
    case 'clear':
      drawing.clearLayer(data.layer_id || 'default');
      break;
  }
});
```

### Server-Side State

The server maintains drawing state for persistence, undo/redo, and broadcast:

```python
from dataclasses import dataclass, field

@dataclass
class DrawingState:
    """Server-side state for drawings."""

    # Elements indexed by layer (slide_index in stardeck)
    elements: dict[int | str, list[DrawingElement]] = field(default_factory=dict)

    # Action history for undo/redo
    undo_stack: list[dict] = field(default_factory=list)
    redo_stack: list[dict] = field(default_factory=list)

    def add_element(self, element: DrawingElement) -> None:
        """Add element and track for undo."""
        layer_id = element.slide_index  # or element.layer_id
        if layer_id not in self.elements:
            self.elements[layer_id] = []
        self.elements[layer_id].append(element)

        # Track for undo
        self.undo_stack.append({"type": "add", "element": element})
        self.redo_stack.clear()  # Clear redo on new action

    def undo(self) -> dict | None:
        """Undo last action."""
        if not self.undo_stack:
            return None
        action = self.undo_stack.pop()
        self.redo_stack.append(action)

        if action["type"] == "add":
            element = action["element"]
            self._remove_element(element.id, element.slide_index)
        elif action["type"] == "clear":
            # Restore cleared elements
            layer_id = action["layer_id"]
            self.elements[layer_id] = action["elements"]
        return action

    def redo(self) -> dict | None:
        """Redo last undone action."""
        if not self.redo_stack:
            return None
        action = self.redo_stack.pop()
        self.undo_stack.append(action)

        if action["type"] == "add":
            element = action["element"]
            layer_id = element.slide_index
            if layer_id not in self.elements:
                self.elements[layer_id] = []
            self.elements[layer_id].append(element)
        elif action["type"] == "clear":
            self.elements[action["layer_id"]] = []
        return action

    def clear_layer(self, layer_id: int | str) -> list[DrawingElement]:
        """Clear all elements from a layer."""
        if layer_id not in self.elements:
            return []
        removed = self.elements[layer_id].copy()
        self.elements[layer_id] = []

        if removed:
            self.undo_stack.append({
                "type": "clear",
                "layer_id": layer_id,
                "elements": removed
            })
            self.redo_stack.clear()
        return removed
```

### Event System

The plugin exposes an event system for the application to hook into:

```javascript
// Drawing plugin events
drawing.on('stroke:start', (tool, point) => {
  // Stroke began - useful for live preview to others
});

drawing.on('stroke:progress', (tool, points) => {
  // Points being added - for real-time preview
});

drawing.on('stroke:complete', (element) => {
  // Stroke finished - element ready to persist
});

drawing.on('element:selected', (elementId) => {
  // Element was selected
});

drawing.on('element:deselected', () => {
  // Selection cleared
});

drawing.on('element:moved', (elementId, newPosition) => {
  // Element was moved
});

drawing.on('element:resized', (elementId, newBounds) => {
  // Element was resized
});

drawing.on('element:deleted', (elementId) => {
  // Element was deleted
});

drawing.on('tool:changed', (newTool, oldTool) => {
  // Drawing tool changed
});

drawing.on('color:changed', (color, type) => {
  // Color changed (type: 'stroke' | 'fill')
});
```

---

## Use Cases

### 1. Stardeck (Presentation Annotations)

The primary use case: presenters annotate slides, annotations sync to audience.

```javascript
// Presenter mode - drawings broadcast to audience
const presenterDrawing = new DrawingLayer(slideContainer, {
  mode: 'broadcast',
  callbacks: {
    onStrokeComplete: async (element) => {
      element.slide_index = currentSlideIndex;
      await fetch(`/api/presenter/draw?token=${presenterToken}`, {
        method: 'POST',
        body: JSON.stringify(element)
      });
    },
    onUndo: () => fetch('/api/presenter/draw/undo', { method: 'POST' }),
    onClear: () => fetch('/api/presenter/draw/clear', { method: 'POST' })
  }
});

// Audience mode - receives broadcasts, can draw locally
const audienceDrawing = new DrawingLayer(slideContainer, {
  mode: 'local',  // Local drawings don't broadcast
  receiveBroadcast: true,  // But we receive presenter's drawings
  layers: [
    { id: 'presenter', editable: false },  // Read-only presenter layer
    { id: 'notes', editable: true }         // Personal notes layer
  ],
  persistence: {
    type: 'localStorage',
    key: (layerId) => `stardeck_notes_slide_${currentSlideIndex}`
  }
});

// SSE subscription for audience
eventSource.addEventListener('datastar-drawing', (event) => {
  const data = JSON.parse(event.data);
  audienceDrawing.applyBroadcast('presenter', data);
});
```

### 2. Whiteboard Applications

Collaborative whiteboards with infinite canvas:

```javascript
const whiteboard = new DrawingLayer(canvas, {
  mode: 'collaborative',
  infiniteCanvas: true,
  panZoom: true,
  tools: ['pen', 'highlighter', 'line', 'arrow', 'rect', 'ellipse',
          'diamond', 'text', 'sticky-note', 'eraser', 'select'],
  callbacks: {
    onStrokeComplete: (element) => {
      websocket.send(JSON.stringify({
        type: 'draw',
        element,
        userId: currentUser.id
      }));
    }
  }
});

// Receive others' drawings via WebSocket
websocket.onmessage = (event) => {
  const { type, element, userId } = JSON.parse(event.data);
  if (type === 'draw' && userId !== currentUser.id) {
    whiteboard.addElement(element, { showCursor: true, cursorLabel: userId });
  }
};
```

### 3. Image Annotation Tools

Medical imaging, photo review, document markup:

```javascript
const annotator = new DrawingLayer(imageContainer, {
  mode: 'local',
  background: loadedImage,
  tools: ['arrow', 'circle', 'rect', 'freehand', 'text', 'measure'],
  callbacks: {
    onStrokeComplete: (element) => {
      annotations.push(element);
      saveAnnotations();
    }
  },
  customTools: {
    measure: {
      icon: 'ruler',
      create: (start, end) => ({
        type: 'measurement',
        points: [start, end],
        distance: calculateDistance(start, end)
      }),
      render: (element) => {
        // Render line with distance label
      }
    }
  }
});

// Export annotations
function exportAnnotations() {
  return annotator.exportAsJSON();
}

function exportAnnotatedImage() {
  return annotator.exportAsPNG({ includeBackground: true });
}
```

### 4. Collaborative Diagramming

Flowcharts, system diagrams, mind maps:

```javascript
const diagramEditor = new DrawingLayer(canvas, {
  mode: 'collaborative',
  grid: { size: 20, snap: true },
  tools: ['select', 'rect', 'ellipse', 'diamond', 'arrow', 'text'],
  connectors: true,  // Enable line connectors between shapes
  callbacks: {
    onStrokeComplete: (element) => {
      crdt.insert(element);  // CRDT for conflict-free sync
    },
    onElementUpdate: (id, changes) => {
      crdt.update(id, changes);
    }
  }
});

// Shape library
const shapeLibrary = [
  { name: 'Process', shape: 'rect', defaultText: 'Process' },
  { name: 'Decision', shape: 'diamond', defaultText: 'Yes/No' },
  { name: 'Start/End', shape: 'ellipse', defaultText: 'Start' },
];

// Drag from library to canvas
shapeLibrary.forEach(template => {
  diagramEditor.addTemplateShape(template);
});
```

### 5. PDF Markup

Document review and annotation:

```javascript
const pdfAnnotator = new DrawingLayer(pdfContainer, {
  mode: 'local',
  layers: pdfPages.map((_, i) => ({ id: `page-${i}` })),
  tools: ['highlight', 'underline', 'strikethrough', 'comment',
          'freehand', 'stamp', 'signature'],
  callbacks: {
    onStrokeComplete: (element) => {
      pdfDocument.addAnnotation(element);
    }
  }
});

// Page navigation updates active layer
pdfViewer.on('pagechange', (pageNum) => {
  pdfAnnotator.setActiveLayer(`page-${pageNum}`);
});

// Export annotated PDF
async function saveAnnotatedPDF() {
  const annotations = pdfAnnotator.exportAllLayers();
  return await pdfDocument.embedAnnotations(annotations);
}
```

### 6. Educational Tools (Teacher/Student)

Teacher draws, students see in real-time. Students can also annotate locally.

```javascript
// Teacher's view
const teacherBoard = new DrawingLayer(canvas, {
  mode: 'broadcast',
  tools: ['pen', 'highlighter', 'arrow', 'rect', 'text', 'equation'],
  callbacks: {
    onStrokeComplete: async (element) => {
      await classroom.broadcast('draw', element);
    }
  },
  customTools: {
    equation: {
      icon: 'formula',
      render: (element) => renderLatex(element.latex)
    }
  }
});

// Student's view
const studentBoard = new DrawingLayer(canvas, {
  mode: 'local',
  receiveBroadcast: true,
  layers: [
    { id: 'teacher', editable: false, opacity: 1 },
    { id: 'mynotes', editable: true, opacity: 0.7 }
  ]
});

// Teacher's drawings appear on student boards
classroom.on('draw', (element) => {
  studentBoard.applyBroadcast('teacher', { action: 'add', element });
});

// Student can toggle between viewing and note-taking
notesToggle.onclick = () => {
  studentBoard.setLayerVisibility('mynotes', !studentBoard.isLayerVisible('mynotes'));
};
```

---

## Advanced Considerations

### Multi-User Collaboration

When multiple users can draw simultaneously:

```javascript
// User presence and cursors
const collaborativeDrawing = new DrawingLayer(canvas, {
  mode: 'collaborative',
  presence: {
    enabled: true,
    showCursors: true,
    showUserLabels: true,
    cursorColors: 'auto'  // Assign unique colors per user
  }
});

// Track user presence
collaboration.on('user:join', (user) => {
  collaborativeDrawing.addUserCursor(user.id, {
    color: user.color,
    label: user.name
  });
});

collaboration.on('user:leave', (userId) => {
  collaborativeDrawing.removeUserCursor(userId);
});

collaboration.on('cursor:move', (userId, position) => {
  collaborativeDrawing.updateUserCursor(userId, position);
});

// Conflict resolution
collaborativeDrawing.setConflictResolver({
  // Last-write-wins for simple cases
  strategy: 'last-write-wins',

  // Or custom resolver for complex cases
  resolve: (local, remote) => {
    if (remote.timestamp > local.timestamp) {
      return remote;
    }
    return local;
  }
});
```

### Undo/Redo Strategies

Different strategies for different use cases:

```javascript
// Per-user undo (each user undoes their own actions)
const drawing = new DrawingLayer(canvas, {
  undoStrategy: 'per-user',
  userId: currentUser.id
});

// Global undo (anyone can undo anyone's last action)
const drawing = new DrawingLayer(canvas, {
  undoStrategy: 'global'
});

// Per-layer undo (undo applies to active layer only)
const drawing = new DrawingLayer(canvas, {
  undoStrategy: 'per-layer'
});

// Server-authoritative undo (for presenter-only scenarios)
const drawing = new DrawingLayer(canvas, {
  undoStrategy: 'server',
  callbacks: {
    onUndo: async () => {
      const result = await fetch('/api/draw/undo', { method: 'POST' });
      return result.json();  // Server returns what was undone
    }
  }
});
```

### Persistence

Multiple persistence options:

```javascript
// localStorage (client-side only)
const drawing = new DrawingLayer(canvas, {
  persistence: {
    type: 'localStorage',
    key: 'my-drawing',
    autoSave: true,
    autoSaveDebounce: 500  // ms
  }
});

// IndexedDB (for larger drawings)
const drawing = new DrawingLayer(canvas, {
  persistence: {
    type: 'indexedDB',
    database: 'drawings',
    store: 'elements'
  }
});

// Server persistence
const drawing = new DrawingLayer(canvas, {
  persistence: {
    type: 'server',
    save: async (elements) => {
      await fetch('/api/drawings', {
        method: 'POST',
        body: JSON.stringify(elements)
      });
    },
    load: async () => {
      const response = await fetch('/api/drawings');
      return response.json();
    }
  }
});

// File-based (for desktop apps)
const drawing = new DrawingLayer(canvas, {
  persistence: {
    type: 'file',
    format: 'svg',  // or 'json'
    path: './drawings/annotation.svg'
  }
});
```

### Export Options

```javascript
// Export as SVG (vector, scalable)
const svg = drawing.exportAsSVG({
  includeBackground: false,
  viewport: { x: 0, y: 0, width: 100, height: 100 }
});

// Export as PNG (raster)
const png = await drawing.exportAsPNG({
  width: 1920,
  height: 1080,
  scale: 2,  // For retina displays
  includeBackground: true,
  backgroundColor: '#ffffff'
});

// Export as JSON (for reimporting)
const json = drawing.exportAsJSON({
  includeMetadata: true,
  format: 'compact'  // or 'pretty'
});

// Export specific layer
const layerSvg = drawing.exportLayerAsSVG('annotations');

// Export with slide/page context (for presentations)
const annotatedSlide = await drawing.exportWithBackground({
  background: slideElement,
  format: 'png'
});
```

### Layers

```javascript
// Multi-layer support
const drawing = new DrawingLayer(canvas, {
  layers: [
    { id: 'background', editable: false, opacity: 1 },
    { id: 'annotations', editable: true, opacity: 1 },
    { id: 'overlay', editable: true, opacity: 0.8 }
  ],
  activeLayer: 'annotations'
});

// Layer operations
drawing.setActiveLayer('overlay');
drawing.setLayerOpacity('annotations', 0.5);
drawing.setLayerVisibility('background', false);
drawing.moveLayerUp('annotations');
drawing.moveLayerDown('overlay');
drawing.mergeLayersDown('overlay');  // Merge into layer below
```

### Permissions

```javascript
// Role-based permissions
const drawing = new DrawingLayer(canvas, {
  permissions: {
    // Determine what current user can do
    canDraw: () => user.role === 'presenter' || user.role === 'collaborator',
    canErase: () => user.role === 'presenter',
    canClear: () => user.role === 'presenter',
    canSelect: (element) => element.created_by === user.id || user.role === 'admin',
    canModify: (element) => element.created_by === user.id || user.role === 'admin',
    canDelete: (element) => element.created_by === user.id || user.role === 'admin',

    // Layer-specific permissions
    canEditLayer: (layerId) => {
      if (layerId === 'presenter') return user.role === 'presenter';
      if (layerId === 'notes') return true;  // Everyone can edit personal notes
      return user.role === 'collaborator';
    }
  }
});

// Server-side permission validation
@rt("/api/draw", methods=["POST"])
async def add_drawing(request, token: str):
    user = validate_token(token)
    if not user.can_draw:
        return JSONResponse({"error": "forbidden"}, status_code=403)

    body = await request.json()

    # Validate element ownership for updates
    if body.get("id"):
        existing = drawing_state.get_element(body["id"])
        if existing and existing.created_by != user.id and not user.is_admin:
            return JSONResponse({"error": "forbidden"}, status_code=403)

    # Process the drawing...
```

---

## API Examples

### Basic Usage

```javascript
// Minimal setup
const drawing = new DrawingLayer(document.getElementById('canvas'));

// With options
const drawing = new DrawingLayer(container, {
  // Initial tool
  tool: 'pen',

  // Default styles
  strokeColor: '#000000',
  strokeWidth: 2,
  fillColor: null,
  opacity: 1,

  // Available tools
  tools: ['select', 'pen', 'line', 'rect', 'ellipse', 'text'],

  // Callbacks
  callbacks: {
    onStrokeComplete: (element) => console.log('New element:', element)
  }
});
```

### Tool Selection

```javascript
// Set active tool
drawing.setTool('pen');
drawing.setTool('rect');
drawing.setTool('select');

// Get current tool
const currentTool = drawing.getTool();

// Tool shortcuts
document.addEventListener('keydown', (e) => {
  switch (e.key) {
    case 'v': drawing.setTool('select'); break;
    case 'p': drawing.setTool('pen'); break;
    case 'l': drawing.setTool('line'); break;
    case 'r': drawing.setTool('rect'); break;
    case 'o': drawing.setTool('ellipse'); break;
    case 't': drawing.setTool('text'); break;
  }
});
```

### Style Control

```javascript
// Set stroke color
drawing.setStrokeColor('#ff0000');

// Set fill color
drawing.setFillColor('#ffff00');
drawing.setFillColor(null);  // No fill

// Set stroke width
drawing.setStrokeWidth(4);

// Set opacity
drawing.setOpacity(0.5);

// Get current styles
const styles = drawing.getStyles();
// { strokeColor: '#ff0000', fillColor: null, strokeWidth: 4, opacity: 0.5 }
```

### Element Manipulation

```javascript
// Add element programmatically
const element = {
  id: 'manual-1',
  type: 'rect',
  x: 10, y: 10,
  width: 30, height: 20,
  stroke_color: '#0000ff',
  stroke_width: 2
};
drawing.addElement(element);

// Remove element
drawing.removeElement('manual-1');

// Update element
drawing.updateElement('manual-1', { x: 20, y: 15 });

// Get all elements
const elements = drawing.getElements();

// Get element by ID
const element = drawing.getElementById('manual-1');

// Clear all elements
drawing.clear();

// Clear specific layer
drawing.clearLayer('annotations');
```

### Selection

```javascript
// Select element
drawing.selectElement('element-1');

// Multi-select
drawing.selectElements(['element-1', 'element-2']);

// Get selected elements
const selected = drawing.getSelectedElements();

// Deselect all
drawing.deselectAll();

// Delete selected
drawing.deleteSelected();

// Move selected
drawing.moveSelected(10, 5);  // dx, dy in percentage units

// Bring to front / send to back
drawing.bringToFront('element-1');
drawing.sendToBack('element-1');
```

### Undo/Redo

```javascript
// Undo last action
drawing.undo();

// Redo last undone action
drawing.redo();

// Check if undo/redo available
const canUndo = drawing.canUndo();
const canRedo = drawing.canRedo();

// Get undo/redo stack sizes
const { undoCount, redoCount } = drawing.getHistoryState();
```

### Receiving Remote Updates

```javascript
// Apply a single remote update
drawing.applyRemoteUpdate({
  action: 'add',
  element: { id: 'remote-1', type: 'pen', ... }
});

drawing.applyRemoteUpdate({
  action: 'remove',
  element_id: 'remote-1'
});

drawing.applyRemoteUpdate({
  action: 'update',
  element_id: 'remote-1',
  changes: { x: 50, y: 50 }
});

drawing.applyRemoteUpdate({
  action: 'clear',
  layer_id: 'presenter'
});

// Batch updates
drawing.applyRemoteUpdates([
  { action: 'add', element: {...} },
  { action: 'add', element: {...} },
  { action: 'remove', element_id: '...' }
]);
```

### Enable/Disable Drawing

```javascript
// Disable drawing (view-only mode)
drawing.disable();

// Enable drawing
drawing.enable();

// Check if enabled
const isEnabled = drawing.isEnabled();

// Toggle
drawing.toggle();
```

### Complete Stardeck Integration Example

```javascript
// Presenter view - full drawing capabilities
function initPresenterDrawing(container, slideIndex, token) {
  const drawing = new DrawingLayer(container, {
    tool: 'pen',
    strokeColor: '#ff0000',
    strokeWidth: 2,
    tools: ['select', 'pen', 'highlighter', 'line', 'arrow',
            'rect', 'ellipse', 'text', 'eraser'],
    callbacks: {
      onStrokeComplete: async (element) => {
        element.slide_index = slideIndex;
        await fetch(`/api/presenter/draw?token=${token}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(element)
        });
      },
      onUndo: async () => {
        const res = await fetch(`/api/presenter/draw/undo?token=${token}`,
          { method: 'POST' });
        return res.json();
      },
      onRedo: async () => {
        const res = await fetch(`/api/presenter/draw/redo?token=${token}`,
          { method: 'POST' });
        return res.json();
      },
      onClear: async () => {
        await fetch(`/api/presenter/draw/clear?token=${token}&slide_index=${slideIndex}`,
          { method: 'POST' });
      }
    }
  });

  return drawing;
}

// Audience view - receives broadcasts + local notes
function initAudienceDrawing(container, slideIndex) {
  const drawing = new DrawingLayer(container, {
    layers: [
      { id: 'presenter', editable: false },
      { id: 'notes', editable: true }
    ],
    activeLayer: 'notes',
    persistence: {
      type: 'localStorage',
      key: `stardeck_notes_${slideIndex}`
    }
  });

  // Connect to SSE for presenter drawings
  const eventSource = new EventSource('/api/events');
  eventSource.addEventListener('datastar-drawing', (event) => {
    const data = JSON.parse(event.data);
    drawing.applyRemoteUpdate(data, 'presenter');
  });

  return drawing;
}

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
  if (e.ctrlKey && e.key === 'z') {
    e.preventDefault();
    drawing.undo();
  }
  if (e.ctrlKey && (e.key === 'y' || (e.shiftKey && e.key === 'z'))) {
    e.preventDefault();
    drawing.redo();
  }
  if (e.key === 'd') {
    drawing.toggle();
  }
  if (e.key === 'Escape') {
    drawing.setTool('select');
    drawing.deselectAll();
  }
});
```

---

## Server-Side Integration (Python/StarHTML)

### Drawing Endpoints

```python
from starlette.responses import JSONResponse
from drawing import DrawingState, parse_element, element_to_dict

# Initialize state
drawing_state = DrawingState()

@rt("/api/draw", methods=["POST"])
async def add_drawing(request, token: str = ""):
    """Add a drawing element."""
    if not validate_token(token):
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    body = await request.json()
    element = parse_element(body)
    drawing_state.add_element(element)

    # Broadcast to other clients
    await broadcast_drawing(element)

    return JSONResponse({"success": True, "id": element.id})

@rt("/api/draw/undo", methods=["POST"])
async def undo_drawing(token: str = ""):
    """Undo last drawing action."""
    if not validate_token(token):
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    action = drawing_state.undo()
    if action:
        await broadcast_undo(action)
        return JSONResponse({"undone": True, "action": action})
    return JSONResponse({"undone": False})

@rt("/api/draw/redo", methods=["POST"])
async def redo_drawing(token: str = ""):
    """Redo last undone action."""
    if not validate_token(token):
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    action = drawing_state.redo()
    if action:
        await broadcast_redo(action)
        return JSONResponse({"redone": True, "action": action})
    return JSONResponse({"redone": False})

@rt("/api/draw/clear", methods=["POST"])
async def clear_drawings(token: str = "", layer_id: str = "default"):
    """Clear all drawings on a layer."""
    if not validate_token(token):
        return JSONResponse({"error": "unauthorized"}, status_code=401)

    removed = drawing_state.clear_layer(layer_id)
    await broadcast_clear(layer_id)

    return JSONResponse({"cleared": True, "count": len(removed)})

@rt("/api/draw/elements")
async def get_elements(layer_id: str = None):
    """Get all drawing elements (or for a specific layer)."""
    if layer_id:
        elements = drawing_state.elements.get(layer_id, [])
    else:
        elements = [el for layer in drawing_state.elements.values() for el in layer]

    return JSONResponse([element_to_dict(el) for el in elements])
```

### SSE Broadcasting

```python
async def broadcast_drawing(element):
    """Broadcast new drawing to all clients."""
    for queue in subscribers:
        try:
            queue.put_nowait({
                "type": "drawing",
                "action": "add",
                "element": element_to_dict(element)
            })
        except asyncio.QueueFull:
            pass

async def broadcast_undo(action):
    """Broadcast undo action."""
    for queue in subscribers:
        try:
            queue.put_nowait({
                "type": "drawing",
                "action": "remove",
                "element_id": action["element"].id,
                "layer_id": action["element"].slide_index
            })
        except asyncio.QueueFull:
            pass

async def broadcast_clear(layer_id):
    """Broadcast clear action."""
    for queue in subscribers:
        try:
            queue.put_nowait({
                "type": "drawing",
                "action": "clear",
                "layer_id": layer_id
            })
        except asyncio.QueueFull:
            pass
```

---

## Summary

The StarHTML drawing plugin provides a flexible, general-purpose drawing layer that can be integrated into various applications:

1. **Presentation tools** (stardeck) - Presenter annotations synced to audience
2. **Whiteboard apps** - Collaborative real-time drawing
3. **Image annotation** - Medical, photo, document markup
4. **Diagramming** - Flowcharts, mind maps
5. **PDF markup** - Document review
6. **Educational tools** - Teacher/student scenarios

Key integration points:
- **Callbacks** for server communication (POST, undo, redo, clear)
- **SSE/WebSocket** for receiving remote updates
- **Event system** for application-level hooks
- **Layers** for separating concerns (presenter vs. personal notes)
- **Permissions** for role-based access control
- **Persistence** options (localStorage, IndexedDB, server, file)
- **Export** formats (SVG, PNG, JSON)

---

## Drawing Tools

### Overview

Each drawing tool follows a common interaction pattern:
1. **Activation** - User selects tool via toolbar or keyboard shortcut
2. **Start** - `pointerdown` event initiates the drawing action
3. **Progress** - `pointermove` events update the preview/path
4. **Commit** - `pointerup` event finalizes the element
5. **Cancel** - `Escape` key or right-click cancels current operation

All tools share common state:
- `stroke_color` - Current stroke color (hex string)
- `stroke_width` - Current stroke width (1-20 range)
- `fill_color` - Fill color for shapes (null = transparent)
- `opacity` - Element opacity (0.0-1.0)

---

### Pen/Freehand Tool

**Purpose:** Draw continuous freehand paths following pointer movement.

**Behavior:**

```
pointerdown:
  1. Create new path with single point at (x, y)
  2. Record pressure if available (stylus)
  3. Begin live preview rendering

pointermove (while drawing):
  1. Sample new point at current (x, y)
  2. Apply point decimation (skip if distance < threshold)
  3. Optionally record pressure value
  4. Update live preview path

pointerup:
  1. Add final point
  2. Apply path smoothing algorithm
  3. Commit element to state
  4. Broadcast to audience (if presenter)
```

**Point Sampling:**

```javascript
// Minimum distance between points (in percentage units)
const MIN_POINT_DISTANCE = 0.5;

function shouldSamplePoint(lastPoint, newPoint) {
    const dx = newPoint.x - lastPoint.x;
    const dy = newPoint.y - lastPoint.y;
    const distance = Math.sqrt(dx * dx + dy * dy);
    return distance >= MIN_POINT_DISTANCE;
}
```

**Pressure Sensitivity:**

Stylus pressure (0.0-1.0) can affect stroke width:

```javascript
function getStrokeWidth(baseWidth, pressure) {
    // Pressure range 0.1-1.0 maps to 0.5x-1.5x width
    const minMultiplier = 0.5;
    const maxMultiplier = 1.5;
    const multiplier = minMultiplier + (pressure * (maxMultiplier - minMultiplier));
    return baseWidth * multiplier;
}
```

For variable-width strokes, render as filled polygon instead of stroked path:

```javascript
function createVariableWidthPath(points, baseWidth) {
    // Calculate perpendicular offsets at each point
    const leftEdge = [];
    const rightEdge = [];

    for (let i = 0; i < points.length; i++) {
        const p = points[i];
        const width = getStrokeWidth(baseWidth, p.pressure) / 2;

        // Calculate tangent direction
        const prev = points[Math.max(0, i - 1)];
        const next = points[Math.min(points.length - 1, i + 1)];
        const dx = next.x - prev.x;
        const dy = next.y - prev.y;
        const len = Math.sqrt(dx * dx + dy * dy) || 1;

        // Perpendicular unit vector
        const px = -dy / len;
        const py = dx / len;

        leftEdge.push({ x: p.x + px * width, y: p.y + py * width });
        rightEdge.push({ x: p.x - px * width, y: p.y - py * width });
    }

    // Combine into closed polygon path
    return [...leftEdge, ...rightEdge.reverse()];
}
```

---

### Line Tool

**Purpose:** Draw straight lines between two points.

**Behavior:**

```
pointerdown:
  1. Record start point (x1, y1)
  2. Create preview line element

pointermove:
  1. Update end point (x2, y2)
  2. Update preview line
  3. If Shift held: constrain to 45-degree increments

pointerup:
  1. Finalize end point
  2. Commit line element
  3. Broadcast to audience
```

**Angle Constraint (Shift key):**

```javascript
function constrainAngle(start, end) {
    const dx = end.x - start.x;
    const dy = end.y - start.y;
    const distance = Math.sqrt(dx * dx + dy * dy);

    // Calculate angle and snap to nearest 45 degrees
    const angle = Math.atan2(dy, dx);
    const snappedAngle = Math.round(angle / (Math.PI / 4)) * (Math.PI / 4);

    return {
        x: start.x + distance * Math.cos(snappedAngle),
        y: start.y + distance * Math.sin(snappedAngle)
    };
}
```

---

### Rectangle Tool

**Purpose:** Draw rectangles by dragging from corner to corner.

**Behavior:**

```
pointerdown:
  1. Record anchor point (corner)
  2. Create preview rectangle

pointermove:
  1. Calculate x, y, width, height from anchor and current point
  2. Handle negative dimensions (dragging left/up)
  3. If Shift held: constrain to square
  4. If Alt held: draw from center (anchor = center)
  5. Update preview

pointerup:
  1. Finalize dimensions
  2. Commit rectangle element
  3. Broadcast to audience
```

**Dimension Calculation:**

```javascript
function calculateRectBounds(anchor, current, fromCenter, constrainSquare) {
    let x, y, width, height;

    if (fromCenter) {
        // Alt key: anchor is center
        const halfWidth = Math.abs(current.x - anchor.x);
        const halfHeight = Math.abs(current.y - anchor.y);

        if (constrainSquare) {
            const size = Math.max(halfWidth, halfHeight);
            x = anchor.x - size;
            y = anchor.y - size;
            width = size * 2;
            height = size * 2;
        } else {
            x = anchor.x - halfWidth;
            y = anchor.y - halfHeight;
            width = halfWidth * 2;
            height = halfHeight * 2;
        }
    } else {
        // Normal: anchor is corner
        x = Math.min(anchor.x, current.x);
        y = Math.min(anchor.y, current.y);
        width = Math.abs(current.x - anchor.x);
        height = Math.abs(current.y - anchor.y);

        if (constrainSquare) {
            const size = Math.max(width, height);
            width = size;
            height = size;
            // Adjust position to maintain anchor corner
            if (current.x < anchor.x) x = anchor.x - size;
            if (current.y < anchor.y) y = anchor.y - size;
        }
    }

    return { x, y, width, height };
}
```

---

### Ellipse Tool

**Purpose:** Draw ellipses/circles by defining bounding box.

**Behavior:**

Same as Rectangle tool, but renders as ellipse within bounding box.

- If **Shift** held: constrain to circle (`width === height`)
- If **Alt** held: draw from center (anchor = center point)

---

### Arrow Tool

**Purpose:** Draw lines with arrowhead markers.

**Behavior:**

Identical to Line tool, but with `end_arrow: true` by default.

**Options:**
- Default: arrow at end only
- UI toggle for arrow placement: None / End only / Start only / Both ends

---

### Text Tool

**Purpose:** Place text annotations on the slide.

**Behavior:**

```
click:
  1. Record position (x, y)
  2. Show text input overlay at position
  3. Focus input field

input:
  1. Live preview text as user types
  2. Auto-resize preview to fit content

Enter or click outside:
  1. If text not empty: commit text element
  2. If text empty: cancel (no element created)

Escape:
  1. Cancel text entry
  2. Remove preview
```

**Multi-line Support:**

- `Enter` without modifier: commit text
- `Shift+Enter`: insert newline
- Text element stores newlines, rendered with `<tspan>` elements

---

### Eraser Tool

**Purpose:** Remove elements by touching them.

**Two Modes:**

**Mode 1: Click Eraser (default)**
```
click:
  1. Hit-test at click position
  2. If element found: delete element, add to undo stack, broadcast
```

**Mode 2: Stroke Eraser (drag)**
```
pointerdown:
  1. Start eraser path, track touched elements (Set)

pointermove:
  1. Hit-test along path
  2. Add touched elements to Set
  3. Visual feedback: ghost/fade touched elements

pointerup:
  1. Delete all touched elements
  2. Add batch deletion to undo stack (single undo restores all)
```

**Hit Testing:**

```javascript
function hitTest(x, y, elements) {
    // Test in reverse order (top elements first)
    for (let i = elements.length - 1; i >= 0; i--) {
        const el = elements[i];
        if (isPointInElement(x, y, el)) {
            return el;
        }
    }
    return null;
}

function isPointInElement(x, y, element) {
    const tolerance = 2; // percentage units

    switch (element.type) {
        case 'pen':
            return isPointNearPath(x, y, element.points, tolerance);
        case 'line':
        case 'arrow':
            return isPointNearLine(x, y, element.points[0], element.points[1], tolerance);
        case 'rect':
            return isPointInRect(x, y, element, tolerance);
        case 'ellipse':
            return isPointInEllipse(x, y, element, tolerance);
        case 'text':
            return isPointInTextBounds(x, y, element);
        default:
            return false;
    }
}

function pointToSegmentDistance(px, py, p1, p2) {
    const dx = p2.x - p1.x;
    const dy = p2.y - p1.y;
    const lengthSq = dx * dx + dy * dy;

    if (lengthSq === 0) {
        return Math.sqrt((px - p1.x) ** 2 + (py - p1.y) ** 2);
    }

    let t = ((px - p1.x) * dx + (py - p1.y) * dy) / lengthSq;
    t = Math.max(0, Math.min(1, t));

    const nearX = p1.x + t * dx;
    const nearY = p1.y + t * dy;

    return Math.sqrt((px - nearX) ** 2 + (py - nearY) ** 2);
}
```

---

### Selection Tool

**Purpose:** Select, move, resize, and delete existing elements.

**Single Selection:**
- Click on element: select it (deselect others), show handles
- Click on empty space: deselect all

**Multi-Selection:**
- Shift+click: toggle element in selection set
- Drag on empty space: create selection rectangle, select intersecting elements

**Move Selected:**
- Drag on selected element: move all selected by delta
- Update preview during drag, commit on release

**Resize Selected:**
- Drag resize handle: calculate new dimensions
- Shift held: maintain aspect ratio
- Handles: 4 corners (NW, NE, SW, SE) + 4 edges (N, S, E, W)

**Selection Handles Visual:**

```
    +-[NW]-----[N]-----[NE]-+
    |                       |
   [W]      (element)      [E]
    |                       |
    +-[SW]-----[S]-----[SE]-+
```

---

### Highlighter Tool

**Purpose:** Semi-transparent marker for highlighting content.

Same as Pen tool, but with fixed visual properties:

```javascript
const HIGHLIGHTER_DEFAULTS = {
    stroke_color: '#FFFF00',     // Yellow
    stroke_width: 20,            // Wide stroke
    opacity: 0.4,                // Semi-transparent
    blendMode: 'multiply'        // Darkens underlying content
};
```

**CSS:**
```css
.highlighter-stroke {
    mix-blend-mode: multiply;
}
```

---

### Diamond Tool

**Purpose:** Draw diamond/rhombus shapes.

Same interaction as Rectangle tool, renders as rotated square (4-point polygon).

```javascript
function diamondToSvg(element) {
    const { x, y, width, height } = element;
    const cx = x + width / 2;
    const cy = y + height / 2;
    const points = [
        `${cx},${y}`,              // top
        `${x + width},${cy}`,      // right
        `${cx},${y + height}`,     // bottom
        `${x},${cy}`               // left
    ].join(' ');
    return `<polygon points="${points}" ... />`;
}
```

---

## Coordinate System

### Percentage-Based Coordinates (0-100)

All drawing coordinates use a **percentage-based system** (0-100) for viewport independence:

- `(0, 0)` = Top-left corner of slide
- `(100, 100)` = Bottom-right corner of slide
- Coordinates can exceed 0-100 range (for elements partially off-screen)

**Benefits:**
- Drawings scale correctly across different screen sizes
- Serialization is resolution-agnostic
- Sync works regardless of audience viewport dimensions

### Coordinate Transformation

**Pointer Event to SVG Coordinates:**

```javascript
function pointerToSvgCoords(event, svgElement) {
    const rect = svgElement.getBoundingClientRect();

    // Get pointer position relative to SVG element
    const x = event.clientX - rect.left;
    const y = event.clientY - rect.top;

    // Convert to percentage (0-100)
    const percentX = (x / rect.width) * 100;
    const percentY = (y / rect.height) * 100;

    return { x: percentX, y: percentY };
}
```

**Using SVG's Built-in Coordinate Transformation:**

```javascript
function pointerToSvgCoords(event, svgElement) {
    const pt = svgElement.createSVGPoint();
    pt.x = event.clientX;
    pt.y = event.clientY;
    const svgPt = pt.matrixTransform(svgElement.getScreenCTM().inverse());
    return { x: svgPt.x, y: svgPt.y };
}
```

### Handling Different Aspect Ratios

The SVG viewBox is set to `0 0 100 100` with `preserveAspectRatio="none"`:

```html
<svg class="drawing-layer" viewBox="0 0 100 100" preserveAspectRatio="none">
```

**Options:**

| Option | Behavior | Trade-off |
|--------|----------|-----------|
| `none` (recommended) | Stretch to fill | Circles may become ellipses |
| `xMidYMid meet` | Maintain ratio, letterbox | Coordinate adjustment needed |
| `xMidYMid slice` | Cover, may crop | Content may be hidden |

**Recommendation:** Use `none` for annotations. Slight distortion is acceptable, and coordinates map 1:1 to viewport percentage.

### Responsive Layout Handling

When the viewport resizes:
1. SVG automatically scales (viewBox handles this)
2. Stroke widths scale proportionally by default
3. No coordinate recalculation needed

**Non-Scaling Strokes:**

```svg
<path d="..." stroke-width="2" vector-effect="non-scaling-stroke" />
```

---

## SVG Rendering

### SVG Layer Structure

```html
<div class="slide-viewport">
    <div class="slide"><!-- Slide content --></div>

    <!-- Presenter drawings layer -->
    <svg class="drawing-layer presenter-layer"
         viewBox="0 0 100 100"
         preserveAspectRatio="none">
        <defs><!-- Markers, patterns --></defs>
        <g class="elements"><!-- Committed elements --></g>
        <g class="preview"><!-- Live preview --></g>
        <g class="selection"><!-- Selection handles --></g>
    </svg>

    <!-- Local notes layer (audience) -->
    <svg class="drawing-layer local-layer" viewBox="0 0 100 100" ...>
    </svg>
</div>
```

### Live Preview During Drawing

Preview elements use distinct styling:

```css
.drawing-layer .preview path,
.drawing-layer .preview line,
.drawing-layer .preview rect,
.drawing-layer .preview ellipse {
    opacity: 0.8;
    pointer-events: none;
}
```

### Final Element Structure

**Pen/Freehand Path:**
```svg
<path id="pen-abc123"
      d="M 10 20 Q 15 22 17.5 24 Q 20 26 25 28 L 30 30"
      stroke="#ff0000" stroke-width="2" fill="none"
      stroke-linecap="round" stroke-linejoin="round" />
```

**Line:**
```svg
<line id="line-def456" x1="10" y1="20" x2="80" y2="60"
      stroke="#0000ff" stroke-width="2" stroke-linecap="round" />
```

**Arrow (with marker):**
```svg
<line id="arrow-ghi789" x1="10" y1="50" x2="80" y2="50"
      stroke="#000" stroke-width="2" marker-end="url(#arrowhead-000000)" />
```

**Rectangle:**
```svg
<rect id="rect-jkl012" x="20" y="30" width="40" height="25"
      stroke="#00ff00" stroke-width="2" fill="none" />
```

**Ellipse:**
```svg
<ellipse id="ellipse-mno345" cx="50" cy="50" rx="30" ry="20"
         stroke="#ff00ff" stroke-width="2" fill="none" />
```

**Text (multi-line):**
```svg
<text id="text-pqr678" x="50" y="50" fill="#000" font-size="4">
    <tspan x="50" dy="0">First line</tspan>
    <tspan x="50" dy="1.2em">Second line</tspan>
</text>
```

### Stroke Properties

| Property | Recommended | Description |
|----------|-------------|-------------|
| `stroke-linecap` | `round` | Rounded stroke ends |
| `stroke-linejoin` | `round` | Rounded corners on path bends |

### Arrow Markers Definition

```svg
<defs>
    <marker id="arrowhead" markerWidth="10" markerHeight="7"
            refX="9" refY="3.5" orient="auto" markerUnits="strokeWidth">
        <polygon points="0 0, 10 3.5, 0 7" fill="currentColor" />
    </marker>
</defs>
```

**Color-Specific Markers:**

Since `currentColor` has inconsistent browser support in markers, generate per-color markers:

```javascript
function ensureArrowMarker(svgDefs, color) {
    const markerId = `arrowhead-${color.replace('#', '')}`;
    if (!svgDefs.querySelector(`#${markerId}`)) {
        // Create marker with fill=color
    }
    return `url(#${markerId})`;
}
```

### Element IDs

Pattern: `{type}-{uuid}` (e.g., `pen-a1b2c3d4`, `rect-e5f6g7h8`)

```javascript
function generateElementId(type) {
    const uuid = crypto.randomUUID().split('-')[0];
    return `${type}-${uuid}`;
}
```

### Z-Index Management

SVG elements render in document order. For z-ordering:

```javascript
function bringToFront(elementId) {
    const el = document.getElementById(elementId);
    el?.parentNode?.appendChild(el);
}

function sendToBack(elementId) {
    const el = document.getElementById(elementId);
    el?.parentNode?.insertBefore(el, el.parentNode.firstChild);
}
```

---

## Path Algorithms

### Point Accumulation During Drawing

```javascript
class PathBuilder {
    constructor(options = {}) {
        this.points = [];
        this.minDistance = options.minDistance ?? 0.5;  // Percentage units
        this.maxPoints = options.maxPoints ?? 10000;
    }

    addPoint(x, y, pressure = 1.0) {
        const point = { x, y, pressure };

        if (this.points.length === 0) {
            this.points.push(point);
            return true;
        }

        if (this.points.length >= this.maxPoints) return false;

        const last = this.points[this.points.length - 1];
        const dist = Math.sqrt((x - last.x) ** 2 + (y - last.y) ** 2);

        if (dist >= this.minDistance) {
            this.points.push(point);
            return true;
        }
        return false;
    }
}
```

### Path Smoothing Algorithms

#### 1. Quadratic Bezier Smoothing (Recommended)

```javascript
function pointsToQuadraticPath(points) {
    if (points.length === 0) return '';
    if (points.length === 1) return `M ${points[0].x} ${points[0].y}`;
    if (points.length === 2) {
        return `M ${points[0].x} ${points[0].y} L ${points[1].x} ${points[1].y}`;
    }

    let d = `M ${points[0].x} ${points[0].y}`;

    for (let i = 1; i < points.length - 1; i++) {
        const p = points[i];
        const next = points[i + 1];
        const midX = (p.x + next.x) / 2;
        const midY = (p.y + next.y) / 2;
        d += ` Q ${p.x} ${p.y} ${midX} ${midY}`;
    }

    const last = points[points.length - 1];
    d += ` L ${last.x} ${last.y}`;

    return d;
}
```

#### 2. Catmull-Rom Spline

Smoother curves that pass through all control points:

```javascript
function pointsToCatmullRomPath(points, tension = 0.5) {
    if (points.length < 2) return '';

    let d = `M ${points[0].x} ${points[0].y}`;

    for (let i = 0; i < points.length - 1; i++) {
        const p0 = points[Math.max(i - 1, 0)];
        const p1 = points[i];
        const p2 = points[Math.min(i + 1, points.length - 1)];
        const p3 = points[Math.min(i + 2, points.length - 1)];

        const t = tension;
        const cp1x = p1.x + (p2.x - p0.x) / 6 * t;
        const cp1y = p1.y + (p2.y - p0.y) / 6 * t;
        const cp2x = p2.x - (p3.x - p1.x) / 6 * t;
        const cp2y = p2.y - (p3.y - p1.y) / 6 * t;

        d += ` C ${cp1x} ${cp1y} ${cp2x} ${cp2y} ${p2.x} ${p2.y}`;
    }

    return d;
}
```

#### 3. Ramer-Douglas-Peucker Simplification

Reduce point count while preserving shape:

```javascript
function simplifyPath(points, epsilon = 0.5) {
    if (points.length <= 2) return points;

    let maxDist = 0, maxIndex = 0;
    const first = points[0], last = points[points.length - 1];

    for (let i = 1; i < points.length - 1; i++) {
        const dist = perpendicularDistance(points[i], first, last);
        if (dist > maxDist) {
            maxDist = dist;
            maxIndex = i;
        }
    }

    if (maxDist > epsilon) {
        const left = simplifyPath(points.slice(0, maxIndex + 1), epsilon);
        const right = simplifyPath(points.slice(maxIndex), epsilon);
        return [...left.slice(0, -1), ...right];
    }

    return [first, last];
}
```

### Pressure Sensitivity Implementation

For variable-width strokes, render as filled polygon:

```javascript
function createPressureSensitivePath(points, baseWidth) {
    if (points.length < 2) return '';

    const leftEdge = [], rightEdge = [];

    for (let i = 0; i < points.length; i++) {
        const p = points[i];
        const pressure = p.pressure ?? 1;
        const halfWidth = (baseWidth * pressure) / 2;

        const prev = points[Math.max(0, i - 1)];
        const next = points[Math.min(points.length - 1, i + 1)];

        let dx = next.x - prev.x, dy = next.y - prev.y;
        const len = Math.sqrt(dx * dx + dy * dy) || 1;
        dx /= len; dy /= len;

        // Perpendicular vector
        const px = -dy, py = dx;

        leftEdge.push({ x: p.x + px * halfWidth, y: p.y + py * halfWidth });
        rightEdge.push({ x: p.x - px * halfWidth, y: p.y - py * halfWidth });
    }

    // Build closed path
    let d = `M ${leftEdge[0].x} ${leftEdge[0].y}`;
    for (let i = 1; i < leftEdge.length; i++) {
        d += ` L ${leftEdge[i].x} ${leftEdge[i].y}`;
    }
    for (let i = rightEdge.length - 1; i >= 0; i--) {
        d += ` L ${rightEdge[i].x} ${rightEdge[i].y}`;
    }
    d += ' Z';

    return d;
}
```

### Complete Path Processing Pipeline

```javascript
class PathProcessor {
    constructor(options = {}) {
        this.simplifyEpsilon = options.simplifyEpsilon ?? 0.5;
        this.smoothingMethod = options.smoothingMethod ?? 'quadratic';
        this.usePressure = options.usePressure ?? false;
    }

    process(rawPoints, baseWidth) {
        if (rawPoints.length === 0) return { type: 'stroke', d: '' };

        // 1. Simplify path
        let points = simplifyPath(rawPoints, this.simplifyEpsilon);

        // 2. Generate SVG path
        if (this.usePressure && this.hasPressureVariation(points)) {
            return {
                type: 'fill',
                d: createPressureSensitivePath(points, baseWidth)
            };
        } else {
            const d = this.smoothingMethod === 'catmull-rom'
                ? pointsToCatmullRomPath(points)
                : pointsToQuadraticPath(points);
            return { type: 'stroke', d };
        }
    }

    hasPressureVariation(points) {
        const pressures = points.map(p => p.pressure ?? 1);
        return Math.max(...pressures) - Math.min(...pressures) > 0.1;
    }
}
```

### Performance Considerations

**Throttled Rendering:**

```javascript
class ThrottledRenderer {
    constructor(drawFn) {
        this.drawFn = drawFn;
        this.pending = false;
    }

    requestRender(data) {
        this.latestData = data;
        if (!this.pending) {
            this.pending = true;
            requestAnimationFrame(() => {
                this.pending = false;
                this.drawFn(this.latestData);
            });
        }
    }
}
```

### Algorithm Comparison

| Algorithm | Smoothness | Performance | Best For |
|-----------|------------|-------------|----------|
| Quadratic Bezier | Good | Fast | General use |
| Catmull-Rom | Excellent | Medium | Precision |
| RDP Simplification | N/A | Fast | Reducing points |

**Recommended Pipeline:**
1. Collect points with minimum distance threshold (0.5%)
2. Apply RDP simplification for long strokes (>100 points)
3. Use quadratic bezier smoothing
4. For stylus with pressure variation, render as filled polygon
