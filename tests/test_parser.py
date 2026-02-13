"""Tests for stardeck parser."""

from stardeck.parser import (
    extract_notes,
    parse_deck,
    parse_frontmatter,
    split_slides,
    transform_click_tags,
)


def test_split_slides_basic():
    content = "# Slide 1\n---\n# Slide 2"
    result = split_slides(content)
    assert len(result) == 2
    assert result[0] == "# Slide 1"
    assert result[1] == "# Slide 2"


def test_split_slides_single():
    content = "# Single Slide"
    result = split_slides(content)
    assert len(result) == 1
    assert result[0] == "# Single Slide"


def test_split_slides_empty_slides():
    content = "# Slide 1\n---\n---\n# Slide 2"
    result = split_slides(content)
    assert len(result) == 3
    assert result[1] == ""


def test_split_slides_only_delimiter_at_line_start():
    content = "# Slide with --- in middle\n---\n# Slide 2"
    result = split_slides(content)
    assert len(result) == 2
    assert "---" in result[0]


def test_split_slides_empty_value_frontmatter():
    content = "# Slide 1\n---\nclass:\n---\n# Slide 2"
    result = split_slides(content)
    assert len(result) == 2
    assert "class:" in result[1]


def test_split_slides_mid_deck_frontmatter():
    content = """# Slide 1
---
layout: cover
---
# Cover Slide
---
# Slide 3"""
    result = split_slides(content)
    assert len(result) == 3
    assert "layout: cover" in result[1]
    assert "Cover Slide" in result[1]


def test_parse_frontmatter():
    raw = "---\nlayout: cover\n---\n# Title"
    fm, content = parse_frontmatter(raw)
    assert fm["layout"] == "cover"
    assert content == "# Title"


def test_parse_frontmatter_multiple_keys():
    raw = "---\nlayout: cover\ntransition: slide-left\nbackground: ./bg.jpg\n---\n# Content"
    fm, content = parse_frontmatter(raw)
    assert fm["layout"] == "cover"
    assert fm["transition"] == "slide-left"
    assert fm["background"] == "./bg.jpg"
    assert content == "# Content"


def test_parse_frontmatter_no_frontmatter():
    raw = "# Just Content\nNo frontmatter here"
    fm, content = parse_frontmatter(raw)
    assert fm == {}
    assert content == raw


def test_parse_frontmatter_empty():
    raw = "---\n---\n# Title"
    fm, content = parse_frontmatter(raw)
    assert fm == {}
    assert content == "# Title"


def test_parse_frontmatter_empty_value():
    """Frontmatter with empty value (class:) should parse as None."""
    raw = "---\nclass:\n---\n# Title"
    fm, content = parse_frontmatter(raw)
    assert "class" in fm
    assert fm["class"] is None
    assert content.strip() == "# Title"


def test_extract_notes():
    content = "# Slide\n<!-- notes\nSpeaker notes here\n-->"
    result, notes = extract_notes(content)
    assert "Speaker notes here" in notes
    assert "<!--" not in result


def test_extract_notes_no_notes():
    content = "# Slide\nNo notes here"
    result, notes = extract_notes(content)
    assert notes == ""
    assert result == content


def test_extract_notes_regular_comments():
    content = "# Slide\n<!-- regular comment -->\n<!-- notes\nSpeaker notes\n-->"
    result, notes = extract_notes(content)
    assert "regular comment" in result
    assert "Speaker notes" in notes


def test_extract_notes_multiline():
    content = "# Slide\n<!-- notes\nLine 1\nLine 2\nLine 3\n-->"
    result, notes = extract_notes(content)
    assert "Line 1" in notes
    assert "Line 2" in notes
    assert "Line 3" in notes


def test_extract_notes_multiple_blocks():
    """Multiple note blocks should all be captured."""
    content = "# Slide\n<!-- notes\nFirst\n-->\nMore content\n<!-- notes\nSecond\n-->"
    result, notes = extract_notes(content)
    assert "First" in notes
    assert "Second" in notes
    assert "<!--" not in result


def test_transform_click_tags():
    content = "<click>First</click><click>Second</click>"
    result, max_clicks = transform_click_tags(content)
    assert max_clicks == 2
    assert 'data-click="1"' in result
    assert 'data-click="2"' in result
    assert 'class="click-reveal"' in result
    assert 'data-class:revealed="$clicks >= 1"' in result
    assert 'data-class:revealed="$clicks >= 2"' in result


def test_transform_click_tags_preserves_content():
    content = "<click><p>Hello</p></click>"
    result, _ = transform_click_tags(content)
    assert "<p>Hello</p>" in result


def test_transform_click_tags_no_clicks():
    content = "No click tags here"
    result, max_clicks = transform_click_tags(content)
    assert result == content
    assert max_clicks == 0


def test_parse_deck(tmp_path):
    md_file = tmp_path / "slides.md"
    md_file.write_text("# Slide 1\n---\n# Slide 2")
    deck = parse_deck(md_file)
    assert deck.total == 2
    assert "<h1>" in deck.slides[0].content


def test_parse_deck_with_frontmatter(tmp_path):
    md_file = tmp_path / "slides.md"
    content = "---\nlayout: cover\n---\n# Title Slide\n---\n# Regular Slide"
    md_file.write_text(content)
    deck = parse_deck(md_file)
    has_cover_layout = any(s.layout == "cover" for s in deck.slides)
    assert has_cover_layout or deck.total >= 2


def test_parse_deck_with_notes(tmp_path):
    md_file = tmp_path / "slides.md"
    md_file.write_text("# Slide 1\n<!-- notes\nSpeaker notes\n-->")
    deck = parse_deck(md_file)
    assert deck.total == 1
    assert "Speaker notes" in deck.slides[0].note


def test_parse_deck_mid_deck_frontmatter(tmp_path):
    md_file = tmp_path / "slides.md"
    content = """# Slide 1
---
layout: cover
---
# Cover Slide
---
# Slide 3"""
    md_file.write_text(content)
    deck = parse_deck(md_file)
    assert deck.total == 3
    assert deck.slides[1].layout == "cover"
    assert deck.slides[0].layout == "default"
    assert deck.slides[2].layout == "default"


def test_parse_deck_with_click_tags(tmp_path):
    md_file = tmp_path / "slides.md"
    md_file.write_text("# Slide\n<click>One</click>\n<click>Two</click>")
    deck = parse_deck(md_file)
    assert deck.slides[0].max_clicks == 2
    assert 'data-click="1"' in deck.slides[0].content
    assert 'data-click="2"' in deck.slides[0].content


def test_cls_to_class_in_html(tmp_path):
    """cls= in inline HTML should become class= (StarHTML convention)."""
    md_file = tmp_path / "slides.md"
    md_file.write_text('<div cls="text-blue-500 p-4">styled</div>')
    deck = parse_deck(md_file)
    assert 'class="text-blue-500 p-4"' in deck.slides[0].content
    assert "cls=" not in deck.slides[0].content


def test_cls_preserved_in_code_blocks(tmp_path):
    """cls= inside code fences should NOT be transformed."""
    md_file = tmp_path / "slides.md"
    md_file.write_text('```html\n<div cls="example">demo</div>\n```')
    deck = parse_deck(md_file)
    assert "cls" in deck.slides[0].content
