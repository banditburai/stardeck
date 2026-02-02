"""Tests for stardeck models."""

from pathlib import Path

from stardeck.models import Deck, DeckConfig, SlideInfo


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


def test_deck_total():
    """Deck should report total number of slides."""
    slides = [
        SlideInfo(content="<h1>One</h1>", raw="# One", index=0, start_line=0, end_line=1),
        SlideInfo(content="<h1>Two</h1>", raw="# Two", index=1, start_line=2, end_line=3),
    ]
    deck = Deck(slides=slides, config=DeckConfig(), filepath=Path("test.md"), raw="# One\n---\n# Two")
    assert deck.total == 2


def test_deck_get_slide():
    """Deck should allow access to slides by index."""
    slides = [
        SlideInfo(content="<h1>One</h1>", raw="# One", index=0, start_line=0, end_line=1),
        SlideInfo(content="<h1>Two</h1>", raw="# Two", index=1, start_line=2, end_line=3),
    ]
    deck = Deck(slides=slides, config=DeckConfig(), filepath=Path("test.md"), raw="# One\n---\n# Two")
    assert deck.slides[0].raw == "# One"
    assert deck.slides[1].raw == "# Two"


def test_slide_info_has_max_clicks():
    """SlideInfo should accept and store max_clicks."""
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
    """SlideInfo max_clicks should default to 0."""
    slide = SlideInfo(
        content="<p>Hello</p>",
        raw="Hello",
        index=0,
        start_line=0,
        end_line=1,
    )
    assert slide.max_clicks == 0
