"""Tests for stardeck models."""

from stardeck.models import DeckConfig, SlideInfo


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


def test_deck_config_defaults():
    """DeckConfig should have sensible defaults."""
    config = DeckConfig()
    assert config.title == "Untitled"
    assert config.theme == "default"
    assert config.aspect_ratio == "16/9"


def test_deck_config_custom_values():
    """DeckConfig should accept custom values."""
    config = DeckConfig(
        title="My Presentation",
        theme="dark",
        aspect_ratio="4/3",
        transition="slide-left",
        code_theme="monokai",
    )
    assert config.title == "My Presentation"
    assert config.theme == "dark"
    assert config.transition == "slide-left"
    assert config.code_theme == "monokai"


def test_deck_config_frozen():
    """DeckConfig should be immutable."""
    config = DeckConfig()
    try:
        config.title = "Changed"  # type: ignore
        assert False, "Should not allow mutation"
    except AttributeError:
        pass  # Expected
