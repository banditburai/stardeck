"""Tests for stardeck parser."""

from stardeck.parser import split_slides


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
