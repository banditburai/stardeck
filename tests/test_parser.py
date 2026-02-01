"""Tests for stardeck parser."""

from stardeck.parser import parse_frontmatter, split_slides


def test_split_slides_basic():
    """split_slides should split by --- delimiter."""
    content = "# Slide 1\n---\n# Slide 2"
    result = split_slides(content)
    assert len(result) == 2
    assert result[0][0] == "# Slide 1"
    assert result[1][0] == "# Slide 2"


def test_split_slides_line_numbers():
    """split_slides should track line numbers."""
    content = "# Slide 1\nMore text\n---\n# Slide 2"
    result = split_slides(content)
    # result is list of (content, start_line, end_line)
    assert result[0][1] == 0  # start_line
    assert result[0][2] == 1  # end_line
    assert result[1][1] == 3  # start_line
    assert result[1][2] == 3  # end_line


def test_split_slides_single():
    """split_slides should handle single slide (no delimiter)."""
    content = "# Single Slide"
    result = split_slides(content)
    assert len(result) == 1
    assert result[0][0] == "# Single Slide"


def test_split_slides_empty_slides():
    """split_slides should handle empty slides between delimiters."""
    content = "# Slide 1\n---\n---\n# Slide 2"
    result = split_slides(content)
    assert len(result) == 3
    assert result[1][0] == ""  # Empty slide between delimiters


def test_split_slides_only_delimiter_at_line_start():
    """split_slides should only split on --- at line start."""
    content = "# Slide with --- in middle\n---\n# Slide 2"
    result = split_slides(content)
    assert len(result) == 2
    assert "---" in result[0][0]  # --- in middle of text preserved


def test_parse_frontmatter():
    """parse_frontmatter should extract YAML and return content."""
    raw = "---\nlayout: cover\n---\n# Title"
    fm, content = parse_frontmatter(raw)
    assert fm["layout"] == "cover"
    assert content == "# Title"


def test_parse_frontmatter_multiple_keys():
    """parse_frontmatter should handle multiple YAML keys."""
    raw = "---\nlayout: cover\ntransition: slide-left\nbackground: ./bg.jpg\n---\n# Content"
    fm, content = parse_frontmatter(raw)
    assert fm["layout"] == "cover"
    assert fm["transition"] == "slide-left"
    assert fm["background"] == "./bg.jpg"
    assert content == "# Content"


def test_parse_frontmatter_no_frontmatter():
    """parse_frontmatter should handle content without frontmatter."""
    raw = "# Just Content\nNo frontmatter here"
    fm, content = parse_frontmatter(raw)
    assert fm == {}
    assert content == raw


def test_parse_frontmatter_empty():
    """parse_frontmatter should handle empty frontmatter."""
    raw = "---\n---\n# Title"
    fm, content = parse_frontmatter(raw)
    assert fm == {}
    assert content == "# Title"
