"""Presenter mode view for StarDeck."""

from starhtml import Div, H3

from stardeck.models import Deck
from stardeck.renderer import render_slide


def create_presenter_view(deck: Deck, slide_index: int = 0) -> Div:
    """Create presenter view with current slide and controls.

    Args:
        deck: The slide deck.
        slide_index: Current slide index.

    Returns:
        StarHTML component for presenter view.
    """
    current_slide = deck.slides[slide_index]

    return Div(
        # Main layout - two panels
        Div(
            # Current slide panel
            Div(
                render_slide(current_slide, deck),
                id="presenter-current",
                cls="presenter-slide-panel",
            ),
            # Info panel (notes, timer, next preview)
            Div(
                # Notes section
                Div(
                    H3("Notes"),
                    Div(
                        current_slide.note or "No notes for this slide.",
                        id="presenter-notes-content",
                        cls="presenter-notes-text",
                    ),
                    id="presenter-notes",
                    cls="presenter-notes-panel",
                ),
                cls="presenter-info-panel",
            ),
            cls="presenter-layout",
        ),
        cls="presenter-root",
    )
