"""Presenter mode view for StarDeck."""

from __future__ import annotations

from typing import TYPE_CHECKING

from starhtml import Button, Div, H3, Signal, Span, get, post

from stardeck.models import Deck
from stardeck.renderer import render_slide

if TYPE_CHECKING:
    from stardeck.server import PresentationState


COLORS = ["#000000", "#ffffff", "#ff0000", "#ffff00", "#00ff00", "#00ffff", "#0000ff", "#ff00ff"]


def create_drawing_toolbar(token: str) -> Div:
    """Create drawing toolbar with tool and action buttons.

    Args:
        token: Presenter authentication token.

    Returns:
        StarHTML Div component for the toolbar.
    """
    return Div(
        # Tool buttons
        Div(
            Button(
                "✏️",
                data_on_click="$drawing_tool = 'pen'",
                cls="tool-btn",
                data_class_active="$drawing_tool === 'pen'",
                title="Pen tool",
            ),
            Button(
                "📏",
                data_on_click="$drawing_tool = 'line'",
                cls="tool-btn",
                data_class_active="$drawing_tool === 'line'",
                title="Line tool",
            ),
            Button(
                "⬜",
                data_on_click="$drawing_tool = 'rect'",
                cls="tool-btn",
                data_class_active="$drawing_tool === 'rect'",
                title="Rectangle tool",
            ),
            Button(
                "⭕",
                data_on_click="$drawing_tool = 'ellipse'",
                cls="tool-btn",
                data_class_active="$drawing_tool === 'ellipse'",
                title="Ellipse tool",
            ),
            Button(
                "➡️",
                data_on_click="$drawing_tool = 'arrow'",
                cls="tool-btn",
                data_class_active="$drawing_tool === 'arrow'",
                title="Arrow tool",
            ),
            cls="toolbar-tools",
        ),
        # Color palette
        Div(
            *[
                Button(
                    "",
                    style=f"background:{c}",
                    data_on_click=f"$stroke_color = '{c}'",
                    cls="color-btn",
                    data_class_active=f"$stroke_color === '{c}'",
                    title=c,
                )
                for c in COLORS
            ],
            cls="color-palette",
        ),
        # Stroke width selector
        Div(
            *[
                Button(
                    "━" * i,
                    data_on_click=f"$stroke_width = {i * 2}",
                    cls="width-btn",
                    data_class_active=f"$stroke_width === {i * 2}",
                    title=f"{i * 2}px",
                )
                for i in [1, 2, 3, 4, 5]
            ],
            cls="width-selector",
        ),
        # Actions
        Div(
            Button(
                "↩️",
                data_on_click=post(f"/api/presenter/draw/undo?token={token}"),
                cls="tool-btn",
                title="Undo",
            ),
            Button(
                "↪️",
                data_on_click=post(f"/api/presenter/draw/redo?token={token}"),
                cls="tool-btn",
                title="Redo",
            ),
            Button(
                "🗑️",
                data_on_click=post(f"/api/presenter/draw/clear?token={token}"),
                cls="tool-btn",
                title="Clear slide drawings",
            ),
            cls="toolbar-actions",
        ),
        cls="drawing-toolbar",
        id="drawing-toolbar",
    )


def create_presenter_view(
    deck: Deck, pres: PresentationState | None = None, *, token: str = ""
) -> Div:
    """Create presenter view with current slide and controls.

    Args:
        deck: The slide deck.
        pres: Presentation state for broadcast sync. If provided, initializes
              from current state and uses broadcast endpoints.
        token: Presenter authentication token for drawing endpoints.

    Returns:
        StarHTML component for presenter view.
    """
    # Initialize from presentation state if available
    slide_index = pres.slide_index if pres else 0
    clicks_val = pres.clicks if pres else 0

    current_slide = deck.slides[slide_index]
    next_slide = deck.slides[slide_index + 1] if slide_index + 1 < deck.total else None

    # Use broadcast endpoints when pres is available
    next_endpoint = "/api/presenter/next" if pres else "/api/slide/next"
    prev_endpoint = "/api/presenter/prev" if pres else "/api/slide/prev"

    return Div(
        # Signals for slide navigation state (enables multi-window sync)
        (slide_idx := Signal("slide_index", slide_index)),
        (total := Signal("total_slides", deck.total)),
        (clicks := Signal("clicks", clicks_val)),
        (max_clicks := Signal("max_clicks", current_slide.max_clicks)),
        # Elapsed timer signal
        (elapsed := Signal("elapsed", 0)),
        # Drawing signals
        Signal("drawing_tool", "pen"),
        Signal("stroke_color", "#ff0000"),
        Signal("stroke_width", 2),
        # Timer increment (every second) - hidden element
        Span(
            data_on_interval=(
                "$elapsed++",
                {"duration": "1s"},
            ),
            style="display: none",
        ),
        # Keyboard navigation - uses broadcast endpoints for presenter→audience sync
        Span(
            data_on_keydown=(
                f"""
                if (evt.key === 'ArrowRight' || evt.key === ' ') {{
                    evt.preventDefault();
                    @get('{next_endpoint}');
                }} else if (evt.key === 'ArrowLeft') {{
                    evt.preventDefault();
                    @get('{prev_endpoint}');
                }}
                """,
                {"window": True},
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
                # Navigation controls - uses broadcast endpoints
                Div(
                    Button(
                        "← Prev",
                        cls="presenter-nav-btn",
                        data_on_click=get(prev_endpoint),
                        data_attr_disabled=slide_idx == 0,
                    ),
                    Span(
                        data_text=slide_idx + 1 + " / " + total,
                        cls="presenter-slide-counter",
                    ),
                    Button(
                        "Next →",
                        cls="presenter-nav-btn",
                        data_on_click=get(next_endpoint),
                        data_attr_disabled=slide_idx == total - 1,
                    ),
                    cls="presenter-nav-bar",
                ),
                cls="presenter-info-panel",
            ),
            cls="presenter-layout",
        ),
        # Drawing toolbar (only shown when token is available)
        create_drawing_toolbar(token) if token else None,
        cls="presenter-root",
    )
