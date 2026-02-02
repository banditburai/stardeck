# Presenter Mode Implementation Plan

> **Epic:** `stardeck-koy`
> **Design:** `docs/designs/2026-02-01-stardeck.md`
> **Research:** `docs/research/slidev-presenter-mode.md`
> **For Claude:** Use `skills/collaboration/execute-plan-with-beads` to implement.

## Overview

Implement Slidev-style presenter mode:
- Separate `/presenter` route
- Current slide + next slide preview
- Speaker notes display
- Elapsed timer
- Multi-window sync via SSE

## Tasks Overview

| ID | Task | Review ID | Blocked By |
|----|------|-----------|------------|
| stardeck-koy.17 | Presenter route scaffold | stardeck-koy.25 | - |
| stardeck-koy.18 | Presenter layout component | stardeck-koy.26 | .17 |
| stardeck-koy.19 | Next slide preview | stardeck-koy.27 | .18 |
| stardeck-koy.20 | Speaker notes display | stardeck-koy.28 | .18 |
| stardeck-koy.21 | Elapsed timer | stardeck-koy.29 | .18 |
| stardeck-koy.22 | Multi-window sync | stardeck-koy.30 | .19, .20 |
| stardeck-koy.23 | Presenter keyboard navigation | stardeck-koy.31 | .22 |
| stardeck-koy.24 | Presenter CSS styling | stardeck-koy.32 | .21, .23 |

---

### Task 17: Presenter route scaffold

**Review:** TBD (P1, blocked by this task)
**Blocked by:** None

**Files:**
- Modify: `stardeck/server.py`
- Create: `stardeck/presenter.py`
- Test: `tests/test_presenter.py`

**Step 1: Write failing test**
```python
def test_presenter_route_exists(client):
    response = client.get("/presenter")
    assert response.status_code == 200
    assert "presenter" in response.text.lower()
```

**Step 2: Verify test fails**
Run: `pytest tests/test_presenter.py -v`

**Step 3: Implement**
Create basic `/presenter` route that returns a placeholder page.

```python
# stardeck/presenter.py
from starhtml import Div, H1

def create_presenter_view(deck, slide_index: int = 0):
    """Create presenter view with current slide and controls."""
    return Div(
        H1("Presenter Mode"),
        cls="presenter-root",
    )
```

Register route in server.py:
```python
@rt("/presenter")
def presenter():
    return create_presenter_view(deck_state["deck"])
```

**Step 4: Verify tests pass**
Run: `pytest tests/test_presenter.py -v`

---

### Task 18: Presenter layout component

**Review:** TBD (P1, blocked by this task)
**Blocked by:** Task 17

**Files:**
- Modify: `stardeck/presenter.py`
- Test: `tests/test_presenter.py`

**Step 1: Write failing test**
```python
def test_presenter_has_current_slide(client):
    response = client.get("/presenter")
    html = response.text
    assert "current-slide" in html or "presenter-current" in html

def test_presenter_has_notes_panel(client):
    response = client.get("/presenter")
    html = response.text
    assert "notes" in html.lower()
```

**Step 2: Implement**
Create two-panel layout:
- Left/Top: Current slide (scaled down)
- Right/Bottom: Notes + controls

```python
def create_presenter_view(deck, slide_index: int = 0):
    current_slide = deck.slides[slide_index]
    return Div(
        (slide_idx := Signal("slide_index", slide_index)),
        # Main layout
        Div(
            # Current slide panel
            Div(
                render_slide(current_slide, deck),
                id="presenter-current",
                cls="presenter-slide-panel",
            ),
            # Info panel (notes, timer, next)
            Div(
                Div(id="presenter-notes", cls="presenter-notes"),
                cls="presenter-info-panel",
            ),
            cls="presenter-layout",
        ),
        cls="presenter-root",
    )
```

---

### Task 19: Next slide preview

**Review:** TBD (P1, blocked by this task)
**Blocked by:** Task 18

**Files:**
- Modify: `stardeck/presenter.py`
- Test: `tests/test_presenter.py`

**Step 1: Write failing test**
```python
def test_presenter_has_next_slide_preview(client):
    response = client.get("/presenter")
    html = response.text
    assert "presenter-next" in html or "next-slide" in html
```

**Step 2: Implement**
Add next slide preview to info panel:
```python
# In info panel
Div(
    H3("Next"),
    Div(
        render_slide(next_slide, deck) if next_slide else "End of presentation",
        id="presenter-next",
        cls="presenter-next-preview",
    ),
),
```

Scale down with CSS transform.

---

### Task 20: Speaker notes display

**Review:** TBD (P1, blocked by this task)
**Blocked by:** Task 18

**Files:**
- Modify: `stardeck/presenter.py`
- Test: `tests/test_presenter.py`

**Step 1: Write failing test**
```python
def test_presenter_shows_speaker_notes(tmp_path):
    """Test that presenter view displays speaker notes from slide."""
    from stardeck.server import create_app

    md_file = tmp_path / "slides.md"
    md_file.write_text("# Slide 1\n\n<!-- notes\nThese are my speaker notes.\n-->")

    app, rt, deck_state = create_app(md_file)
    client = TestClient(app)

    response = client.get("/presenter")
    assert "speaker notes" in response.text.lower() or "notes" in response.text.lower()
```

**Step 2: Implement**
Display `slide.note` content (already parsed):
```python
Div(
    H3("Notes"),
    Div(
        current_slide.note or "No notes for this slide.",
        id="presenter-notes-content",
        cls="presenter-notes-text",
    ),
    cls="presenter-notes-panel",
),
```

---

### Task 21: Elapsed timer

**Review:** TBD (P1, blocked by this task)
**Blocked by:** Task 18

**Files:**
- Modify: `stardeck/presenter.py`
- Test: `tests/test_presenter.py`

**Step 1: Write failing test**
```python
def test_presenter_has_timer(client):
    response = client.get("/presenter")
    html = response.text
    assert "timer" in html.lower() or "elapsed" in html.lower()
```

**Step 2: Implement**
Add client-side timer using Datastar signals:
```python
(elapsed := Signal("elapsed", 0)),

# Timer display
Div(
    data_text="Math.floor($elapsed / 60).toString().padStart(2, '0') + ':' + ($elapsed % 60).toString().padStart(2, '0')",
    cls="presenter-timer",
),

# Timer increment (every second)
Span(
    data_on_interval=(
        "$elapsed++",
        {"duration": "1s"},
    ),
    style="display: none",
),
```

---

### Task 22: Multi-window sync (presenter→audience)

**Review:** TBD (P1, blocked by this task)
**Blocked by:** Task 19, Task 20

**Files:**
- Modify: `stardeck/server.py`
- Modify: `stardeck/presenter.py`
- Test: `tests/test_presenter.py`

**Step 1: Write failing test**
```python
def test_presenter_navigation_updates_audience(client):
    """Test that presenter navigation triggers SSE for all clients."""
    response = client.get("/presenter")
    html = response.text
    # Presenter should have navigation that updates server state
    assert "/api/slide/" in html
```

**Step 2: Implement**

**Option A: Shared server state (simpler)**
- Presenter navigates via same SSE endpoints
- All connected clients (audience + presenter) receive updates
- Already works with current architecture!

**Option B: BroadcastChannel (client-side)**
- Use BroadcastChannel API for same-origin sync
- No server changes needed

**Recommended: Option A** - Already have SSE infrastructure.

Presenter navigation calls same endpoints:
```python
# Presenter keyboard handler
Span(
    data_on_keydown=(
        """
        if (evt.key === 'ArrowRight' || evt.key === ' ') {
            evt.preventDefault();
            if ($clicks < $max_clicks) {
                $clicks++;
            } else {
                @get('/api/slide/next');
            }
        }
        """,
        {"window": True},
    ),
    style="display: none",
),
```

---

### Task 23: Presenter keyboard navigation

**Review:** TBD (P1, blocked by this task)
**Blocked by:** Task 22

**Files:**
- Modify: `stardeck/presenter.py`
- Test: `tests/test_presenter.py`

**Step 1: Write failing test**
```python
def test_presenter_has_keyboard_navigation(client):
    response = client.get("/presenter")
    html = response.text
    assert "data-on-keydown" in html or "data-on:keydown" in html
```

**Step 2: Implement**
Add full keyboard navigation (same as audience view):
- Arrow keys for navigation
- Click handling
- Escape for overview (future)

---

### Task 24: Presenter CSS styling

**Review:** TBD (P1, blocked by this task)
**Blocked by:** Task 21, Task 23

**Files:**
- Modify: `stardeck/themes/default/styles.css`
- Test: Manual visual verification

**Step 1: Add presenter CSS**
```css
/* Presenter Mode */
.presenter-root {
    width: 100vw;
    height: 100vh;
    background: var(--bg-dark);
    color: var(--text-primary);
    overflow: hidden;
}

.presenter-layout {
    display: grid;
    grid-template-columns: 2fr 1fr;
    gap: 1rem;
    height: 100%;
    padding: 1rem;
}

.presenter-slide-panel {
    background: var(--bg-slide);
    border-radius: 8px;
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: center;
}

.presenter-slide-panel .slide {
    transform: scale(0.8);
    transform-origin: center;
}

.presenter-info-panel {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}

.presenter-next-preview {
    background: var(--bg-slide);
    border-radius: 8px;
    aspect-ratio: 16/9;
    overflow: hidden;
    transform: scale(0.5);
    transform-origin: top left;
}

.presenter-notes-panel {
    flex: 1;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 8px;
    padding: 1rem;
    overflow-y: auto;
}

.presenter-timer {
    font-size: 2rem;
    font-variant-numeric: tabular-nums;
    text-align: center;
    padding: 0.5rem;
    background: rgba(255, 255, 255, 0.1);
    border-radius: 4px;
}
```

---

## Execution Notes

### Existing Infrastructure

StarDeck already has:
- Speaker notes parsing (`slide.note` from `<!-- notes -->` comments)
- SSE navigation endpoints
- Click state management
- Signal-based reactivity

### Testing Strategy

- Unit tests for presenter route and components
- Integration tests for navigation sync
- Manual E2E test with two browser windows

### After Implementation

Test with demo deck:
1. Open `http://localhost:8000` in window 1 (audience)
2. Open `http://localhost:8000/presenter` in window 2 (presenter)
3. Navigate from presenter window
4. Verify audience window follows
