"""Presenter mode view for StarDeck."""

from starhtml import Div, H1

from stardeck.models import Deck


def create_presenter_view(deck: Deck, slide_index: int = 0):
    """Create presenter view with current slide and controls.

    Args:
        deck: The slide deck.
        slide_index: Current slide index.

    Returns:
        StarHTML component for presenter view.
    """
    return Div(
        H1("Presenter Mode"),
        cls="presenter-root",
    )
