"""Tests for stardeck models."""

from stardeck.models import Deck, DeckConfig, SlideInfo


def test_slide_info_basic():
    slide = SlideInfo(content="<h1>Hi</h1>", index=0)
    assert slide.index == 0
    assert slide.layout == "default"
    assert slide.transition == "fade"


def test_slide_info_with_frontmatter():
    slide = SlideInfo(
        content="<h1>Hi</h1>",
        index=0,
        frontmatter={"layout": "cover", "transition": "slide-left"},
    )
    assert slide.layout == "cover"
    assert slide.transition == "slide-left"


def test_slide_info_background():
    slide = SlideInfo(
        content="<h1>Hi</h1>",
        index=0,
        frontmatter={"background": "./stars.jpg"},
    )
    assert slide.background == "./stars.jpg"


def test_slide_info_frozen():
    slide = SlideInfo(content="<h1>Hi</h1>", index=0)
    try:
        slide.index = 5  # type: ignore
        assert False, "Should not allow mutation"
    except AttributeError:
        pass


def test_deck_config_defaults():
    config = DeckConfig()
    assert config.title == "Untitled"
    assert config.transition == "fade"


def test_deck_config_custom_values():
    config = DeckConfig(title="My Presentation", transition="slide-left")
    assert config.title == "My Presentation"
    assert config.transition == "slide-left"


def test_deck_config_frozen():
    config = DeckConfig()
    try:
        config.title = "Changed"  # type: ignore
        assert False, "Should not allow mutation"
    except AttributeError:
        pass


def test_deck_total():
    slides = [
        SlideInfo(content="<h1>One</h1>", index=0),
        SlideInfo(content="<h1>Two</h1>", index=1),
    ]
    deck = Deck(slides=slides, config=DeckConfig())
    assert deck.total == 2


def test_slide_info_has_max_clicks():
    slide = SlideInfo(content="<p>Hello</p>", index=0, max_clicks=3)
    assert slide.max_clicks == 3


def test_slide_info_max_clicks_defaults_to_zero():
    slide = SlideInfo(content="<p>Hello</p>", index=0)
    assert slide.max_clicks == 0
