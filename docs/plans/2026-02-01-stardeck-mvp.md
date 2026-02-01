# StarDeck MVP Implementation Plan

> **Epic:** `stardeck-oyf`
> **Design:** `docs/designs/2026-02-01-stardeck.md`
> **For Claude:** Use `skills/collaboration/execute-plan-with-beads` to implement.

## Tasks Overview

| Task ID | Task | Review ID | Blocked By |
|---------|------|-----------|------------|
| stardeck-oyf.10 | Project setup | stardeck-oyf.24 | - |
| stardeck-oyf.11 | SlideInfo dataclass | stardeck-oyf.25 | .10 |
| stardeck-oyf.12 | DeckConfig dataclass | stardeck-oyf.26 | .10 |
| stardeck-oyf.13 | Deck dataclass | stardeck-oyf.27 | .11, .12 |
| stardeck-oyf.14 | Slide splitting | stardeck-oyf.28 | .10 |
| stardeck-oyf.15 | Frontmatter extraction | stardeck-oyf.30 | .14 |
| stardeck-oyf.16 | Notes extraction | stardeck-oyf.29 | .14 |
| stardeck-oyf.17 | parse_deck function | stardeck-oyf.31 | .13, .15, .16 |
| stardeck-oyf.18 | Code block renderer | stardeck-oyf.32 | .13 |
| stardeck-oyf.19 | Slide renderer | stardeck-oyf.33 | .13, .18 |
| stardeck-oyf.20 | Server shell | stardeck-oyf.34 | .17, .19 |
| stardeck-oyf.21 | SSE navigation endpoints | stardeck-oyf.35 | .20 |
| stardeck-oyf.22 | Keyboard navigation | stardeck-oyf.36 | .21 |
| stardeck-oyf.23 | CLI entry point | stardeck-oyf.37 | .20 |

---

### Task 1: Project setup

**Files:**
- Create: `stardeck/__init__.py`
- Create: `stardeck/models.py` (empty)
- Create: `stardeck/parser.py` (empty)
- Create: `stardeck/renderer.py` (empty)
- Create: `stardeck/server.py` (empty)
- Create: `stardeck/cli.py` (empty)
- Modify: `pyproject.toml` (add dependencies)

**Step 1: Create package structure**
```bash
mkdir -p stardeck
touch stardeck/__init__.py
touch stardeck/models.py
touch stardeck/parser.py
touch stardeck/renderer.py
touch stardeck/server.py
touch stardeck/cli.py
```

**Step 2: Update pyproject.toml with dependencies**
Add: starhtml, markdown-it-py, mdit-py-plugins, pygments, pyyaml, click

**Step 3: Verify**
```bash
uv sync
python -c "import stardeck"
```

---

### Task 2: SlideInfo dataclass

**Files:**
- Create: `tests/test_models.py`
- Modify: `stardeck/models.py`

**Step 1: Write failing test**
```python
def test_slide_info_basic():
    slide = SlideInfo(content="<h1>Hi</h1>", raw="# Hi", index=0, start_line=0, end_line=1)
    assert slide.index == 0
    assert slide.layout == "default"
    assert slide.transition == "fade"
```

**Step 2: Verify test fails**
```bash
uv run pytest tests/test_models.py::test_slide_info_basic -v
```

**Step 3: Implement SlideInfo**
Frozen dataclass with content, raw, index, start_line, end_line, frontmatter, note, title.
Properties: layout, transition, background.

**Step 4: Verify tests pass**
```bash
uv run pytest tests/test_models.py -v
```

---

### Task 3: DeckConfig dataclass

**Files:**
- Modify: `tests/test_models.py`
- Modify: `stardeck/models.py`

**Step 1: Write failing test**
```python
def test_deck_config_defaults():
    config = DeckConfig()
    assert config.title == "Untitled"
    assert config.theme == "default"
    assert config.aspect_ratio == "16/9"
```

**Step 2: Verify test fails**

**Step 3: Implement DeckConfig**
Frozen dataclass with title, theme, aspect_ratio, transition, code_theme.

**Step 4: Verify tests pass**

---

### Task 4: Deck dataclass

**Files:**
- Modify: `tests/test_models.py`
- Modify: `stardeck/models.py`

**Step 1: Write failing test**
```python
def test_deck_total():
    slides = [SlideInfo(...), SlideInfo(...)]
    deck = Deck(slides=slides, config=DeckConfig(), filepath=Path("test.md"), raw="...")
    assert deck.total == 2
```

**Step 2: Verify test fails**

**Step 3: Implement Deck**
Dataclass with slides, config, filepath, raw. Property: total.

**Step 4: Verify tests pass**

---

### Task 5: Slide splitting

**Files:**
- Create: `tests/test_parser.py`
- Modify: `stardeck/parser.py`

**Step 1: Write failing test**
```python
def test_split_slides_basic():
    content = "# Slide 1\n---\n# Slide 2"
    result = split_slides(content)
    assert len(result) == 2
    assert result[0][0] == "# Slide 1"
    assert result[1][0] == "# Slide 2"
```

**Step 2: Verify test fails**

**Step 3: Implement split_slides**
Split by `---` delimiter, track line numbers.

**Step 4: Verify tests pass**

---

### Task 6: Frontmatter extraction

**Files:**
- Modify: `tests/test_parser.py`
- Modify: `stardeck/parser.py`

**Step 1: Write failing test**
```python
def test_parse_frontmatter():
    raw = "---\nlayout: cover\n---\n# Title"
    fm, content = parse_frontmatter(raw)
    assert fm["layout"] == "cover"
    assert content == "# Title"
```

**Step 2: Verify test fails**

**Step 3: Implement parse_frontmatter**
Extract YAML between --- delimiters using PyYAML.

**Step 4: Verify tests pass**

---

### Task 7: Notes extraction

**Files:**
- Modify: `tests/test_parser.py`
- Modify: `stardeck/parser.py`

**Step 1: Write failing test**
```python
def test_extract_notes():
    content = "# Slide\n<!-- notes\nSpeaker notes here\n-->"
    result, notes = extract_notes(content)
    assert "Speaker notes here" in notes
    assert "<!--" not in result
```

**Step 2: Verify test fails**

**Step 3: Implement extract_notes**
Regex to find and extract `<!-- notes ... -->` blocks.

**Step 4: Verify tests pass**

---

### Task 8: parse_deck function

**Files:**
- Modify: `tests/test_parser.py`
- Modify: `stardeck/parser.py`

**Step 1: Write failing test**
```python
def test_parse_deck(tmp_path):
    md_file = tmp_path / "slides.md"
    md_file.write_text("# Slide 1\n---\n# Slide 2")
    deck = parse_deck(md_file)
    assert deck.total == 2
    assert "<h1>" in deck.slides[0].content
```

**Step 2: Verify test fails**

**Step 3: Implement parse_deck**
Combine split_slides, parse_frontmatter, extract_notes. Use markdown-it-py to render.

**Step 4: Verify tests pass**

---

### Task 9: Code block renderer

**Files:**
- Create: `tests/test_renderer.py`
- Modify: `stardeck/renderer.py`

**Step 1: Write failing test**
```python
def test_render_code_block():
    result = render_code_block("print('hi')", "python")
    assert "code-block" in str(result)
    # Pygments adds syntax highlighting spans
```

**Step 2: Verify test fails**

**Step 3: Implement render_code_block**
Use Pygments to highlight, wrap in StarHTML Pre/Code components.

**Step 4: Verify tests pass**

---

### Task 10: Slide renderer

**Files:**
- Modify: `tests/test_renderer.py`
- Modify: `stardeck/renderer.py`

**Step 1: Write failing test**
```python
def test_render_slide():
    slide = SlideInfo(content="<h1>Hi</h1>", raw="# Hi", index=0, ...)
    deck = Deck(slides=[slide], config=DeckConfig(), ...)
    result = render_slide(slide, deck)
    assert "slide-0" in str(result)
    assert "layout-default" in str(result)
```

**Step 2: Verify test fails**

**Step 3: Implement render_slide**
Wrap content in StarHTML Div with layout classes, transitions, backgrounds.

**Step 4: Verify tests pass**

---

### Task 11: Server shell

**Files:**
- Create: `tests/test_server.py`
- Modify: `stardeck/server.py`

**Step 1: Write failing test**
```python
def test_create_app(tmp_path):
    md_file = tmp_path / "slides.md"
    md_file.write_text("# Test")
    app, rt, deck = create_app(md_file)
    assert deck.total == 1
```

**Step 2: Verify test fails**

**Step 3: Implement create_app**
Create star_app with signals, render first slide, add navigation bar.

**Step 4: Verify tests pass**

---

### Task 12: SSE navigation endpoints

**Files:**
- Modify: `tests/test_server.py`
- Modify: `stardeck/server.py`

**Step 1: Write failing test**
```python
def test_next_slide_endpoint(client):
    # Test that /api/slide/next returns SSE with updated slide
    response = client.get("/api/slide/next")
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
```

**Step 2: Verify test fails**

**Step 3: Implement SSE endpoints**
Add `/api/slide/next`, `/api/slide/prev`, `/api/slide/{idx}` with @sse decorator.

**Step 4: Verify tests pass**

---

### Task 13: Keyboard navigation

**Files:**
- Modify: `stardeck/server.py`

**Step 1: Add keyboard handler**
Add hidden Span with `data_on_keydown__window` that triggers navigation on arrow keys.

**Step 2: Manual test**
Run server, verify arrow keys navigate slides.

---

### Task 14: CLI entry point

**Files:**
- Create: `tests/test_cli.py`
- Modify: `stardeck/cli.py`
- Modify: `pyproject.toml` (add script entry)

**Step 1: Write failing test**
```python
def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "stardeck" in result.output.lower()
```

**Step 2: Verify test fails**

**Step 3: Implement CLI**
Click group with `run` command. Add `[project.scripts]` to pyproject.toml.

**Step 4: Verify tests pass**
```bash
uv run stardeck --help
```

---

## Execution Notes

- Each task is ~2-5 minutes
- TDD: Write test → fail → implement → pass → commit
- Reviews surface at P1 after each task closes
- Use `bd ready` to see next available work
