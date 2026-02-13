"""Presenter mode view for StarDeck."""

from __future__ import annotations

from typing import TYPE_CHECKING

from starhtml import Button, Div, H3, Signal, Span, get
from starhtml.datastar import js

from star_drawing import DrawingCanvas, drawing_toolbar

from stardeck.models import Deck
from stardeck.renderer import render_slide

if TYPE_CHECKING:
    from stardeck.server import PresentationState


def create_presenter_view(
    deck: Deck, pres: PresentationState | None = None, *, token: str = ""
) -> Div:
    slide_index = pres.slide_index if pres else 0
    clicks_val = pres.clicks if pres else 0

    current_slide = deck.slides[slide_index]
    next_slide = deck.slides[slide_index + 1] if slide_index + 1 < deck.total else None

    next_endpoint = "/api/presenter/next" if pres else "/api/slide/next"
    prev_endpoint = "/api/presenter/prev" if pres else "/api/slide/prev"

    # Drawing canvas + event wiring (only when authenticated)
    if token:
        canvas = DrawingCanvas(
            name="presenter_drawing",
            id="presenter-canvas",
            style="position:absolute;inset:0;width:100%;height:100%;z-index:100;",
            viewbox_width=160,
            viewbox_height=90,
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

    # Signals (defined before grid cards so they can reference them)
    slide_idx = Signal("slide_index", slide_index)
    total = Signal("total_slides", deck.total)
    pres_scale = Signal("pres_scale", 1)
    grid_open = Signal("grid_open", False)

    # Build grid cards for overview mode
    grid_cards = []
    for slide in deck.slides:
        idx = slide.index
        grid_cards.append(
            Div(
                Div(
                    render_slide(slide, deck),
                    cls="grid-slide-inner",
                ),
                Span(str(idx + 1), cls="grid-slide-number"),
                cls="grid-slide-card",
                data_class_current=slide_idx == idx,
                data_on_click=[grid_open.set(False), get(f"/api/presenter/goto/{idx}")],
            ),
        )

    return Div(
        slide_idx,
        total,
        Signal("clicks", clicks_val),
        Signal("max_clicks", current_slide.max_clicks),
        (elapsed := Signal("elapsed", 0)),
        grid_open,
        Span(data_on_interval=(elapsed.add(1), {"duration": "1s"}), style="display:none"),
        Span(
            data_on_keydown=(
                js(f"""
                if (evt.key === 'g' || evt.key === 'o') {{
                    evt.preventDefault();
                    $grid_open = !$grid_open;
                }} else if (evt.key === 'Escape') {{
                    if ($grid_open) {{ evt.preventDefault(); $grid_open = false; }}
                }} else if (!$grid_open) {{
                    if (evt.key === 'ArrowRight' || evt.key === ' ') {{
                        evt.preventDefault();
                        @get('{next_endpoint}');
                    }} else if (evt.key === 'ArrowLeft') {{
                        evt.preventDefault();
                        @get('{prev_endpoint}');
                    }}
                }}
                """),
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
                    (js("$resize_width") / 1920).min(js("$resize_height") / 1080)
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
                    data_text="Math.floor($elapsed / 60).toString().padStart(2, '0') + ':' + ($elapsed % 60).toString().padStart(2, '0')",
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
                toolbar or "",
                Div(
                    Button("← Prev", cls="presenter-nav-btn", data_on_click=get(prev_endpoint), data_attr_disabled=slide_idx == 0),
                    Button(data_text=slide_idx + 1 + " / " + total, cls="presenter-slide-counter", data_on_click=grid_open.toggle()),
                    Button("Next →", cls="presenter-nav-btn", data_on_click=get(next_endpoint), data_attr_disabled=slide_idx == total - 1),
                    cls="presenter-nav-bar",
                ),
                cls="presenter-bottom-bar",
            ),
            cls="presenter-layout",
        ),
        Div(
            Div(*grid_cards, cls="grid-container"),
            cls="overview-grid-modal",
            data_class_active=grid_open,
            data_on_click=js("if (evt.target === this) $grid_open = false"),
            data_effect=js("""
                if ($grid_open) {
                    requestAnimationFrame(() => {
                        const root = document.querySelector('.presenter-root');
                        const sw = parseFloat(getComputedStyle(root).getPropertyValue('--slide-width'));
                        document.querySelectorAll('.grid-slide-card').forEach(card => {
                            const inner = card.querySelector('.grid-slide-inner');
                            if (inner) inner.style.transform = 'scale(' + (card.offsetWidth / sw) + ')';
                        });
                    });
                }
            """),
        ),
        cls="presenter-root",
    )
