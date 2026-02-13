"""Presenter mode view for StarDeck."""

from typing import TYPE_CHECKING

from star_drawing import DrawingCanvas, drawing_toolbar
from starhtml import H3, Button, Div, Signal, Span, get
from starhtml.datastar import evt, js, seq

from stardeck.models import Deck
from stardeck.renderer import (
    SLIDE_HEIGHT,
    SLIDE_WIDTH,
    VIEWBOX_HEIGHT,
    VIEWBOX_WIDTH,
    build_grid_cards,
    build_grid_modal,
    render_slide,
)

if TYPE_CHECKING:  # avoid circular import
    from stardeck.server import PresentationState


def create_presenter_view(deck: Deck, pres: "PresentationState", *, token: str = "") -> Div:
    current_slide = deck.slides[pres.slide_index]
    next_slide = deck.slides[pres.slide_index + 1] if pres.slide_index + 1 < deck.total else None

    next_endpoint = "/api/presenter/next"
    prev_endpoint = "/api/presenter/prev"

    if token:
        canvas = DrawingCanvas(
            name="presenter_drawing",
            id="presenter-canvas",
            style="position:absolute;inset:0;width:100%;height:100%;z-index:100;",
            viewbox_width=VIEWBOX_WIDTH,
            viewbox_height=VIEWBOX_HEIGHT,
            default_stroke_color="#e4e4e7",
        )
        drawing_overlay = Div(
            canvas,
            id="drawing-canvas-wrapper",
            data_on_element_change=js(f"""
                fetch('/api/presenter/changes?token={token}', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{
                        changes: evt.detail,
                        slide_index: $slide_index,
                    }}),
                }})
            """),
        )
        toolbar = drawing_toolbar(canvas)
    else:
        drawing_overlay = None
        toolbar = None

    slide_idx = Signal("slide_index", pres.slide_index)
    total = Signal("total_slides", deck.total)
    elapsed = Signal("elapsed", 0)
    pres_scale = Signal("pres_scale", 1)
    grid_open = Signal("grid_open", False)

    grid_cards = build_grid_cards(
        deck,
        slide_idx,
        grid_open,
        lambda idx: f"/api/presenter/goto/{idx}",
    )

    is_right = (evt.key == "ArrowRight") | (evt.key == " ")
    is_left = evt.key == "ArrowLeft"
    is_grid_key = (evt.key == "g") | (evt.key == "o")
    is_esc = evt.key == "Escape"
    not_grid = ~grid_open

    return Div(
        slide_idx,
        total,
        Signal("clicks", pres.clicks),
        Signal("max_clicks", current_slide.max_clicks),
        elapsed,
        grid_open,
        Span(data_on_interval=(elapsed.add(1), {"duration": "1s"}), style="display:none"),
        Span(
            data_on_keydown=(
                [
                    is_grid_key.then(seq(evt.preventDefault(), grid_open.toggle())),
                    (is_esc & grid_open).then(seq(evt.preventDefault(), grid_open.set(False))),
                    (not_grid & is_right).then(seq(evt.preventDefault(), get(next_endpoint))),
                    (not_grid & is_left).then(seq(evt.preventDefault(), get(prev_endpoint))),
                ],
                {"window": True},
            ),
            style="display:none",
        ),
        Div(
            Div(
                pres_scale,
                Div(
                    Div(render_slide(current_slide, deck), id="presenter-slide-content"),
                    drawing_overlay,
                    cls="slide-scaler",
                    data_attr_style="transform: translate(-50%, -50%) scale(" + pres_scale + ")",
                ),
                id="presenter-current",
                cls="presenter-slide-panel",
                data_resize=pres_scale.set(
                    (js("$resize_width") / SLIDE_WIDTH).min(js("$resize_height") / SLIDE_HEIGHT)
                ),
            ),
            Div(
                Div(
                    H3("Next"),
                    Div(
                        render_slide(next_slide, deck) if next_slide else "End of presentation",
                        id="presenter-next",
                        cls="presenter-next-preview",
                    ),
                    cls="presenter-next-panel",
                ),
                Div(
                    data_text=js(
                        "Math.floor($elapsed/60).toString().padStart(2,'0')+':'+($elapsed%60).toString().padStart(2,'0')"
                    ),
                    cls="presenter-timer",
                ),
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
            Div(
                toolbar,
                Div(
                    Button(
                        "← Prev",
                        cls="presenter-nav-btn",
                        data_on_click=get(prev_endpoint),
                        data_attr_disabled=slide_idx == 0,
                    ),
                    Button(
                        data_text=slide_idx + 1 + " / " + total,
                        cls="presenter-slide-counter",
                        data_on_click=grid_open.toggle(),
                    ),
                    Button(
                        "Next →",
                        cls="presenter-nav-btn",
                        data_on_click=get(next_endpoint),
                        data_attr_disabled=slide_idx == total - 1,
                    ),
                    cls="presenter-nav-bar",
                ),
                cls="presenter-bottom-bar",
            ),
            cls="presenter-layout",
        ),
        build_grid_modal(grid_cards, grid_open, "presenter-root"),
        cls="presenter-root",
    )
