"""Tests for stardeck models."""

from stardeck.models import SlideInfo


def test_slide_info_basic():
    """SlideInfo should store slide data with sensible defaults."""
    slide = SlideInfo(
        content="<h1>Hi</h1>",
        raw="# Hi",
        index=0,
        start_line=0,
        end_line=1,
    )
    assert slide.index == 0
    assert slide.layout == "default"
    assert slide.transition == "fade"


def test_slide_info_with_frontmatter():
    """SlideInfo should use frontmatter values for layout/transition."""
    slide = SlideInfo(
        content="<h1>Hi</h1>",
        raw="# Hi",
        index=0,
        start_line=0,
        end_line=1,
        frontmatter={"layout": "cover", "transition": "slide-left"},
    )
    assert slide.layout == "cover"
    assert slide.transition == "slide-left"


def test_slide_info_background():
    """SlideInfo should expose background from frontmatter."""
    slide = SlideInfo(
        content="<h1>Hi</h1>",
        raw="# Hi",
        index=0,
        start_line=0,
        end_line=1,
        frontmatter={"background": "./stars.jpg"},
    )
    assert slide.background == "./stars.jpg"


def test_slide_info_frozen():
    """SlideInfo should be immutable."""
    slide = SlideInfo(
        content="<h1>Hi</h1>",
        raw="# Hi",
        index=0,
        start_line=0,
        end_line=1,
    )
    try:
        slide.index = 5  # type: ignore
        assert False, "Should not allow mutation"
    except AttributeError:
        pass  # Expected
