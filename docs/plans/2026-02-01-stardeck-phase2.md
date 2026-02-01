# StarDeck Phase 2 Implementation Plan

> **Epic:** `stardeck-70c`
> **Design:** `docs/designs/2026-02-01-stardeck.md`
> **For Claude:** Use `skills/collaboration/execute-plan-with-beads` to implement.

## Tasks Overview

| Task ID | Task | Review ID | Blocked By |
|---------|------|-----------|------------|
| stardeck-70c.1 | URL hash read on load | stardeck-70c.8 | - |
| stardeck-70c.2 | URL hash update on navigation | stardeck-70c.9 | stardeck-70c.1 |
| stardeck-70c.3 | Watch mode file detection | stardeck-70c.10 | - |
| stardeck-70c.4 | Watch mode SSE reload signal | stardeck-70c.11 | stardeck-70c.3 |
| stardeck-70c.5 | Watch mode client handler | stardeck-70c.12 | stardeck-70c.4 |
| stardeck-70c.6 | Slidev transitions research | stardeck-70c.13 | - |
| stardeck-70c.7 | CSS transitions implementation | stardeck-70c.14 | stardeck-70c.6 |

---

## Feature 1: URL Hash Synchronization

### Task 1: URL hash read on load

**Files:**
- Modify: `stardeck/server.py`
- Create: `tests/test_url_hash.py`

**Step 1: Write failing test**
```python
# tests/test_url_hash.py
def test_goto_slide_endpoint_exists(test_client):
    """Verify /api/slide/{idx} endpoint works for deep linking."""
    response = test_client.get("/api/slide/3")
    assert response.status_code == 200
```

**Step 2: Verify test passes** (endpoint already exists from MVP)

**Step 3: Add client-side hash reading**
In the home() route, add a Script that reads `window.location.hash` on load and calls `/api/slide/{idx}`:

```python
Script("""
    const hash = window.location.hash;
    if (hash && hash.startsWith('#')) {
        const idx = parseInt(hash.slice(1), 10);
        if (!isNaN(idx) && idx > 0) {
            // Datastar will handle the navigation
            fetch('/api/slide/' + (idx - 1));
        }
    }
""")
```

**Step 4: Manual test**
- Run server, navigate to `http://localhost:5001/#3`
- Should load slide 3

---

### Task 2: URL hash update on navigation

**Files:**
- Modify: `stardeck/server.py`

**Step 1: Add hash update to SSE responses**
After each navigation, the client should update the URL hash. Add a script element or use Datastar's capabilities to update `window.location.hash`.

**Step 2: Implement via Datastar signal watcher**
Add a hidden element that watches `slide_index` and updates the hash:

```python
Script(
    data_on_signal_change="slide_index",
    data_on_change="window.history.replaceState(null, '', '#' + ($slide_index + 1))"
)
```

Or use a simpler approach: include hash update in the SSE response JavaScript.

**Step 3: Manual test**
- Navigate through slides with arrow keys
- URL should update to `#1`, `#2`, `#3`, etc.
- Refresh page - should stay on current slide

---

## Feature 2: Watch Mode (Hot Reload)

### Task 3: Watch mode file detection

**Files:**
- Create: `stardeck/watch.py`
- Create: `tests/test_watch.py`

**Step 1: Write failing test**
```python
# tests/test_watch.py
import asyncio
from pathlib import Path
from stardeck.watch import create_file_watcher

def test_file_watcher_detects_change(tmp_path):
    """Watcher should detect file modification."""
    md_file = tmp_path / "slides.md"
    md_file.write_text("# Slide 1")

    changes_detected = []

    async def run_test():
        watcher = create_file_watcher(md_file, lambda: changes_detected.append(True))
        # Start watcher in background
        task = asyncio.create_task(watcher.start())
        await asyncio.sleep(0.1)

        # Modify file
        md_file.write_text("# Slide 1 modified")
        await asyncio.sleep(0.5)

        task.cancel()

    asyncio.run(run_test())
    assert len(changes_detected) > 0
```

**Step 2: Verify test fails**

**Step 3: Implement file watcher**
```python
# stardeck/watch.py
from pathlib import Path
from watchfiles import awatch
from typing import Callable

class FileWatcher:
    def __init__(self, path: Path, on_change: Callable[[], None]):
        self.path = path
        self.on_change = on_change
        self._running = False

    async def start(self):
        self._running = True
        async for changes in awatch(self.path):
            if not self._running:
                break
            for change_type, changed_path in changes:
                if Path(changed_path) == self.path:
                    self.on_change()

    def stop(self):
        self._running = False

def create_file_watcher(path: Path, on_change: Callable[[], None]) -> FileWatcher:
    return FileWatcher(path, on_change)
```

**Step 4: Verify tests pass**

---

### Task 4: Watch mode SSE reload signal

**Files:**
- Modify: `stardeck/server.py`
- Modify: `stardeck/watch.py`

**Step 1: Design the reload mechanism**
When file changes:
1. Re-parse the deck
2. Send SSE event to all connected clients
3. Clients re-fetch current slide

**Step 2: Add reload endpoint**
```python
@rt("/api/reload")
@sse
def reload_slide(slide_index: int = 0):
    """Re-render current slide after file change."""
    nonlocal deck
    deck = parse_deck(deck_path)
    idx = min(slide_index, deck.total - 1)
    yield signals(slide_index=idx, total_slides=deck.total)
    yield elements(render_slide(deck.slides[idx], deck), "#slide-content", "inner")
```

**Step 3: Integrate watcher with server**
The watcher needs to trigger a reload. This is tricky with SSE - we may need to use starhtml's live reload feature or implement a polling mechanism.

**Step 4: Test manually**
- Run server with `--reload` flag
- Edit markdown file
- Browser should update

---

### Task 5: Watch mode client handler

**Files:**
- Modify: `stardeck/server.py`
- Modify: `stardeck/cli.py`

**Step 1: Add `--watch` flag to CLI**
```python
@click.option("--watch", "-w", is_flag=True, help="Watch for file changes")
def run(slides: Path, port: int, host: str, watch: bool):
    app, rt, deck = create_app(slides, debug=watch)
```

**Step 2: Connect watcher to SSE**
Option A: Use starhtml's built-in live reload (`live=True`)
Option B: Custom SSE channel for reload events

**Step 3: Test the full flow**
- `stardeck run slides.md --watch`
- Edit slides.md
- Browser auto-updates

---

## Feature 3: Slidev Transitions Comparison

### Task 6: Slidev transitions research

**Files:**
- Create: `docs/research/slidev-transitions.md`

**Step 1: Research Slidev's transition system**
Document:
- What transitions does Slidev support? (fade, slide-left, slide-right, slide-up, slide-down, etc.)
- How are they specified in frontmatter?
- What CSS/JS powers them?
- How does Motion.dev compare?

**Step 2: Create comparison document**
```markdown
# Slidev Transitions Research

## Slidev Built-in Transitions
- fade
- slide-left / slide-right
- slide-up / slide-down
- cover-left / cover-right / cover-up / cover-down
- None

## Frontmatter Syntax
---
transition: slide-left
---

## Implementation Approach for StarDeck
...
```

**Step 3: Identify which transitions to implement first**
Prioritize: fade, slide-left, slide-right (most common)

---

### Task 7: CSS transitions implementation

**Files:**
- Modify: `stardeck/themes/default/styles.css`
- Modify: `stardeck/renderer.py`

**Step 1: Add transition CSS**
The default theme already has some transitions. Enhance them:

```css
/* Transitions */
.transition-fade {
    animation: fadeIn 0.3s ease-out;
}

.transition-slide-left {
    animation: slideInFromRight 0.3s ease-out;
}

.transition-slide-right {
    animation: slideInFromLeft 0.3s ease-out;
}

@keyframes slideInFromRight {
    from { transform: translateX(100%); opacity: 0; }
    to { transform: translateX(0); opacity: 1; }
}

@keyframes slideInFromLeft {
    from { transform: translateX(-100%); opacity: 0; }
    to { transform: translateX(0); opacity: 1; }
}
```

**Step 2: Wire up transition class in renderer**
Ensure `render_slide()` applies the correct `transition-{name}` class based on frontmatter.

**Step 3: Test with demo slides**
Add slides with different transitions to demo_slides.md and verify they work.

---

## Execution Notes

- Tasks 1-2 (URL hash) can run in parallel with Tasks 3-5 (watch mode)
- Task 6 (research) can run in parallel with everything
- Task 7 (transitions) depends on Task 6 research findings
- Each task is ~5-15 minutes
- TDD: Write test → fail → implement → pass → commit
