# Phase 3: Click Animations Implementation Plan

> **Epic:** `stardeck-koy`
> **Design:** `docs/designs/2026-02-01-stardeck.md`
> **For Claude:** Use `skills/collaboration/execute-plan-with-beads` to implement.

## Overview

Implement Slidev-style click animations using the Hybrid approach:
- Client handles click increments locally (instant, no latency)
- Server provides slide content with embedded `max_clicks`
- SSE only triggers on slide changes, not per-click
- Uses StarHTML Signal objects (not raw `$clicks` strings)

## Tasks Overview

| ID | Task | Review ID | Blocked By |
|----|------|-----------|------------|
| stardeck-koy.1 | Model: Add max_clicks to SlideInfo | stardeck-koy.9 | - |
| stardeck-koy.2 | Parser: Count click tags | stardeck-koy.10 | .1 |
| stardeck-koy.3 | Parser: Transform click tags to HTML | stardeck-koy.11 | .2 |
| stardeck-koy.4 | Server: Add clicks signal | stardeck-koy.12 | .1 |
| stardeck-koy.5 | Server: Click navigation logic | stardeck-koy.13 | .3, .4 |
| stardeck-koy.6 | Server: SSE endpoints reset clicks | stardeck-koy.14 | .5 |
| stardeck-koy.7 | CSS: Click reveal animations | stardeck-koy.15 | .3 |
| stardeck-koy.8 | URL: Hash support for clicks | stardeck-koy.16 | .5 |

---

### Task 1: Model - Add max_clicks to SlideInfo

**Review:** TBD (P1, blocked by this task)
**Blocked by:** None

**Files:**
- Modify: `stardeck/models.py`
- Test: `tests/test_models.py`

**Step 1: Write failing test**
```python
def test_slide_info_has_max_clicks():
    slide = SlideInfo(
        content="<p>Hello</p>",
        raw="Hello",
        index=0,
        start_line=0,
        end_line=1,
        max_clicks=3,
    )
    assert slide.max_clicks == 3

def test_slide_info_max_clicks_defaults_to_zero():
    slide = SlideInfo(
        content="<p>Hello</p>",
        raw="Hello",
        index=0,
        start_line=0,
        end_line=1,
    )
    assert slide.max_clicks == 0
```

**Step 2: Verify test fails**
Run: `pytest tests/test_models.py -v`

**Step 3: Implement**
Add `max_clicks: int = 0` field to `SlideInfo` dataclass.

**Step 4: Verify tests pass**
Run: `pytest tests/test_models.py -v`

---

### Task 2: Parser - Count click tags

**Review:** TBD (P1, blocked by this task)
**Blocked by:** Task 1

**Files:**
- Modify: `stardeck/parser.py`
- Test: `tests/test_parser.py`

**Step 1: Write failing test**
```python
def test_count_click_tags():
    from stardeck.parser import count_click_tags

    content = """
    <click>First</click>
    <click>Second</click>
    <click>Third</click>
    """
    assert count_click_tags(content) == 3

def test_count_click_tags_empty():
    from stardeck.parser import count_click_tags
    assert count_click_tags("No clicks here") == 0

def test_count_click_tags_nested():
    from stardeck.parser import count_click_tags
    # Each <click> is one step, nesting doesn't add extra
    content = "<click><click>Nested</click></click>"
    assert count_click_tags(content) == 2
```

**Step 2: Verify test fails**
Run: `pytest tests/test_parser.py::test_count_click_tags -v`

**Step 3: Implement**
```python
def count_click_tags(content: str) -> int:
    """Count the number of <click> tags in content."""
    return len(re.findall(r'<click[^>]*>', content, re.IGNORECASE))
```

**Step 4: Verify tests pass**
Run: `pytest tests/test_parser.py -v`

---

### Task 3: Parser - Transform click tags to HTML

**Review:** TBD (P1, blocked by this task)
**Blocked by:** Task 2

**Files:**
- Modify: `stardeck/parser.py`
- Test: `tests/test_parser.py`

**Step 1: Write failing test**
```python
def test_transform_click_tags():
    from stardeck.parser import transform_click_tags

    content = "<click>First</click><click>Second</click>"
    result, max_clicks = transform_click_tags(content)

    assert max_clicks == 2
    assert 'data-click="1"' in result
    assert 'data-click="2"' in result
    assert 'class="click-reveal"' in result

def test_transform_click_tags_preserves_content():
    from stardeck.parser import transform_click_tags

    content = "<click><p>Hello</p></click>"
    result, _ = transform_click_tags(content)

    assert "<p>Hello</p>" in result
```

**Step 2: Verify test fails**

**Step 3: Implement**
```python
def transform_click_tags(content: str) -> tuple[str, int]:
    """Transform <click>...</click> to data-show divs.

    Returns (transformed_content, max_clicks).
    """
    pattern = r'<click>(.*?)</click>'
    matches = list(re.finditer(pattern, content, re.DOTALL))

    if not matches:
        return content, 0

    max_clicks = len(matches)
    result = content

    # Replace in reverse to preserve indices
    for i, match in enumerate(reversed(matches), 1):
        click_num = max_clicks - i + 1
        replacement = f'<div class="click-reveal" data-click="{click_num}">{match.group(1)}</div>'
        result = result[:match.start()] + replacement + result[match.end():]

    return result, max_clicks
```

**Step 4: Integrate into parse_deck**
Call `transform_click_tags` before markdown rendering, store `max_clicks` in SlideInfo.

---

### Task 4: Server - Add clicks signal

**Review:** TBD (P1, blocked by this task)
**Blocked by:** Task 1

**Files:**
- Modify: `stardeck/server.py`
- Test: `tests/test_server.py`

**Step 1: Write failing test**
```python
def test_home_has_clicks_signal(client):
    response = client.get("/")
    html = response.text
    assert "clicks" in html
    # Verify signal initialization
    assert 'data-signals' in html
```

**Step 2: Implement**
In `home()`, add clicks signal using StarHTML syntax:
```python
(clicks := Signal("clicks", 0)),
```

**Step 3: Read max_clicks from slide data attribute**
```python
# Use js() for DOM access
(max_clicks := Signal("max_clicks", js("parseInt(document.querySelector('[data-max-clicks]')?.dataset.maxClicks || '0', 10)"))),
```

Or better - pass max_clicks from Python:
```python
(max_clicks := Signal("max_clicks", initial_slide.max_clicks)),
```

---

### Task 5: Server - Click navigation logic

**Review:** TBD (P1, blocked by this task)
**Blocked by:** Task 3, Task 4

**Files:**
- Modify: `stardeck/server.py`
- Test: `tests/test_server.py`

**Step 1: Write failing test**
```python
def test_keyboard_navigation_with_clicks(client):
    # Test that navigation handler exists and includes click logic
    response = client.get("/")
    html = response.text
    # Should have click increment logic
    assert "clicks" in html
    assert "max_clicks" in html
```

**Step 2: Implement navigation handler**

Using StarHTML Signal methods:
```python
# Keyboard navigation with click support
Span(
    data_on_keydown=(
        [
            # Forward: Right/Space
            ((evt.key == "ArrowRight") | (evt.key == " ")).then(
                (clicks < max_clicks).if_(
                    clicks.add(1),  # Increment clicks locally
                    [clicks.set(0), get("/api/slide/next")]  # Next slide via SSE
                )
            ),
            # Backward: Left
            (evt.key == "ArrowLeft").then(
                (clicks > 0).if_(
                    clicks.sub(1),  # Decrement clicks locally
                    get("/api/slide/prev")  # Prev slide via SSE
                )
            ),
        ],
        {"window": True},
    ),
    style="display: none",
),
```

**Note:** May need `js()` wrapper for complex conditional logic.

---

### Task 6: Server - SSE endpoints reset clicks

**Review:** TBD (P1, blocked by this task)
**Blocked by:** Task 5

**Files:**
- Modify: `stardeck/server.py`
- Test: `tests/test_server.py`

**Step 1: Write failing test**
```python
def test_next_slide_resets_clicks(client):
    # SSE response should include clicks=0
    response = client.get("/api/slide/next?slide_index=0")
    # Verify clicks signal is reset
    assert "clicks" in response.text
```

**Step 2: Implement**
Update SSE endpoints to yield `clicks=0` (and `max_clicks` for new slide):
```python
@rt("/api/slide/next")
@sse
def next_slide(slide_index: int = 0):
    new_idx = min(slide_index + 1, deck.total - 1)
    new_slide = deck.slides[new_idx]

    yield signals(
        slide_index=new_idx,
        clicks=0,  # Reset clicks
        max_clicks=new_slide.max_clicks,  # New slide's max
    )
    yield elements(render_slide(new_slide, deck), "#slide-content", "inner")
```

---

### Task 7: CSS - Click reveal animations

**Review:** TBD (P1, blocked by this task)
**Blocked by:** Task 3

**Files:**
- Modify: `stardeck/themes/default/styles.css`
- Test: Manual visual verification

**Step 1: Add click-reveal styles**
```css
/* Click reveals - hidden by default */
.click-reveal {
    opacity: 0;
    transform: translateY(10px);
    transition: opacity 0.3s ease-out, transform 0.3s ease-out;
    pointer-events: none;
}

/* Revealed state - controlled by Datastar data-show */
.click-reveal[data-show="true"] {
    opacity: 1;
    transform: translateY(0);
    pointer-events: auto;
}
```

**Step 2: Add data-show attributes in renderer**
The renderer needs to add `data-show` based on clicks signal.
This requires modifying the HTML post-processing to inject:
```html
<div class="click-reveal" data-click="1" data-show="$clicks >= 1">...</div>
```

**Alternative:** Use `data-effect` to toggle visibility classes.

---

### Task 8: URL - Hash support for clicks

**Review:** TBD (P1, blocked by this task)
**Blocked by:** Task 5

**Files:**
- Modify: `stardeck/server.py`
- Test: `tests/test_server.py`

**Step 1: Write failing test**
```python
def test_url_hash_includes_clicks(client):
    response = client.get("/")
    html = response.text
    # Should have URL hash sync with clicks
    # Format: #slide or #slide.click
    assert "history.replaceState" in html or "location.hash" in html
```

**Step 2: Implement**
Add `data-effect` for URL hash sync:
```python
Span(
    data_effect=js("""
        const hash = ($slide_index + 1) + ($clicks > 0 ? '.' + $clicks : '');
        window.history.replaceState(null, '', '#' + hash);
    """),
    style="display: none",
),
```

**Step 3: Parse hash on load**
Update load handler to parse `#3.2` as slide 3, click 2.

---

## Execution Notes

### StarHTML Signal Patterns

**DO use:**
```python
(clicks := Signal("clicks", 0))
data_show=clicks >= 1
clicks.add(1)
clicks.set(0)
```

**DON'T use:**
```python
data_show="$clicks >= 1"  # Raw string - wrong!
```

### Datastar Integration

Click elements need `data-show` with signal reference. Two approaches:

1. **Inject at render time**: Parser adds `data-show="$clicks >= N"` string (Datastar parses)
2. **Use data-effect**: Effect toggles CSS classes based on `clicks` signal

Approach 1 is simpler but mixes raw JS strings. Approach 2 is more StarHTML-idiomatic but requires effect logic.

### Testing Strategy

- Unit tests for parser (count, transform)
- Unit tests for model (max_clicks field)
- Integration tests for server (signals present, SSE resets)
- Manual E2E test with demo_slides.md containing `<click>` tags
