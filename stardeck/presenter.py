"""Presenter mode view for StarDeck."""

from starhtml import Button, Div, H3, Signal, Span, get

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
    next_slide = deck.slides[slide_index + 1] if slide_index + 1 < deck.total else None

    return Div(
        # Signals for slide navigation state (enables multi-window sync)
        (slide_idx := Signal("slide_index", slide_index)),
        (total := Signal("total_slides", deck.total)),
        (clicks := Signal("clicks", 0)),
        (max_clicks := Signal("max_clicks", current_slide.max_clicks)),
        # Elapsed timer signal
        (elapsed := Signal("elapsed", 0)),
        # Timer increment (every second) - hidden element
        Span(
            data_on_interval=(
                "$elapsed++",
                {"duration": "1s"},
            ),
            style="display: none",
        ),
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
                # Next slide preview
                Div(
                    H3("Next"),
                    Div(
                        render_slide(next_slide, deck) if next_slide else "End of presentation",
                        id="presenter-next",
                        cls="presenter-next-preview",
                    ),
                    cls="presenter-next-panel",
                ),
                # Elapsed timer display
                Div(
                    data_text="Math.floor($elapsed / 60).toString().padStart(2, '0') + ':' + ($elapsed % 60).toString().padStart(2, '0')",
                    cls="presenter-timer",
                ),
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
                # Navigation controls (triggers SSE for multi-window sync)
                Div(
                    Button(
                        "← Prev",
                        cls="presenter-nav-btn",
                        data_on_click=get("/api/slide/prev"),
                        data_attr_disabled=slide_idx == 0,
                    ),
                    Span(
                        data_text=slide_idx + 1 + " / " + total,
                        cls="presenter-slide-counter",
                    ),
                    Button(
                        "Next →",
                        cls="presenter-nav-btn",
                        data_on_click=get("/api/slide/next"),
                        data_attr_disabled=slide_idx == total - 1,
                    ),
                    cls="presenter-nav-bar",
                ),
                cls="presenter-info-panel",
            ),
            cls="presenter-layout",
        ),
        cls="presenter-root",
    )
