"""Unit tests for PresentationState — pure state machine, no HTTP."""

from stardeck.models import Deck, DeckConfig, SlideInfo
from stardeck.server import PresentationState


def _deck(*max_clicks_per_slide: int) -> Deck:
    """Build a minimal Deck with the given max_clicks per slide."""
    slides = [
        SlideInfo(content=f"<h1>Slide {i}</h1>", index=i, max_clicks=mc)
        for i, mc in enumerate(max_clicks_per_slide)
    ]
    return Deck(slides=slides, config=DeckConfig())


# --- TestNext ---


def test_next_increments_clicks_below_max():
    pres = PresentationState(_deck(2, 0))
    pres.next()
    assert pres.slide_index == 0
    assert pres.clicks == 1


def test_next_advances_slide_at_max_clicks():
    pres = PresentationState(_deck(1, 0))
    pres.clicks = 1
    pres.next()
    assert pres.slide_index == 1
    assert pres.clicks == 0


def test_next_noop_at_last_slide_max_clicks():
    pres = PresentationState(_deck(0, 0))
    pres.slide_index = 1
    pres.next()
    assert pres.slide_index == 1


def test_next_resets_clicks_on_advance():
    pres = PresentationState(_deck(2, 3))
    pres.clicks = 2
    pres.next()
    assert pres.slide_index == 1
    assert pres.clicks == 0


# --- TestPrev ---


def test_prev_decrements_clicks_above_zero():
    pres = PresentationState(_deck(3, 0))
    pres.clicks = 2
    pres.prev()
    assert pres.slide_index == 0
    assert pres.clicks == 1


def test_prev_goes_to_prev_slide_at_zero_clicks():
    pres = PresentationState(_deck(2, 0))
    pres.slide_index = 1
    pres.clicks = 0
    pres.prev()
    assert pres.slide_index == 0
    assert pres.clicks == 2  # prev slide's max_clicks


def test_prev_noop_at_first_slide_zero_clicks():
    pres = PresentationState(_deck(0, 0))
    pres.prev()
    assert pres.slide_index == 0
    assert pres.clicks == 0


def test_prev_sets_clicks_to_prev_slide_max():
    pres = PresentationState(_deck(5, 0))
    pres.slide_index = 1
    pres.prev()
    assert pres.clicks == 5


# --- TestGotoSlide ---


def test_goto_basic():
    pres = PresentationState(_deck(0, 0, 0))
    pres.goto_slide(2)
    assert pres.slide_index == 2
    assert pres.clicks == 0


def test_goto_clamps_index_high():
    pres = PresentationState(_deck(0, 0))
    pres.goto_slide(99)
    assert pres.slide_index == 1


def test_goto_clamps_index_low():
    pres = PresentationState(_deck(0, 0))
    pres.goto_slide(-5)
    assert pres.slide_index == 0


def test_goto_clamps_clicks_to_max():
    pres = PresentationState(_deck(2, 0))
    pres.goto_slide(0, clicks=100)
    assert pres.clicks == 2


def test_goto_accepts_valid_clicks():
    pres = PresentationState(_deck(3, 0))
    pres.goto_slide(0, clicks=2)
    assert pres.clicks == 2


# --- TestReloadDeck ---


def test_reload_clamps_slide_index():
    pres = PresentationState(_deck(0, 0, 0))
    pres.slide_index = 2
    pres.reload_deck(_deck(0))  # now only 1 slide
    assert pres.slide_index == 0


def test_reload_clamps_clicks():
    pres = PresentationState(_deck(5))
    pres.clicks = 5
    pres.reload_deck(_deck(2))  # max_clicks now 2
    assert pres.clicks == 2


def test_reload_preserves_in_bounds_state():
    pres = PresentationState(_deck(3, 3, 3))
    pres.slide_index = 1
    pres.clicks = 2
    pres.reload_deck(_deck(3, 3, 3))
    assert pres.slide_index == 1
    assert pres.clicks == 2
