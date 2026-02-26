from collections.abc import Callable
from typing import TYPE_CHECKING

from star_drawing import DrawingCanvas, drawing_toolbar
from starhtml import H3, Button, Div, NotStr, Signal, Span, get
from starhtml.datastar import evt, js, seq

from stardeck.models import Deck, SlideInfo

if TYPE_CHECKING:
    from stardeck.server import PresentationState

SLIDE_WIDTH = 1920
SLIDE_HEIGHT = 1080
VIEWBOX_WIDTH = 160
VIEWBOX_HEIGHT = 90

HASH_UPDATE_EFFECT = js(
    "window.history.replaceState(null, '', '#' + ($slide_index + 1) + ($clicks > 0 ? '.' + $clicks : ''))"
)


_IMAGE_LAYOUTS = frozenset({"image-left", "image-right", "hero", "caption"})


def _resolve_asset_url(raw: str) -> str:
    if raw.startswith(("http://", "https://", "/", "data:")):
        return raw
    if raw.startswith("./"):
        return raw[1:]
    return f"/{raw}"


def render_slide(slide: SlideInfo, deck: Deck) -> Div:
    transition = slide.frontmatter.get("transition") or deck.config.transition

    classes = [
        f"slide-{slide.index}",
        f"layout-{slide.layout}",
        f"transition-{transition}",
        "slide",
    ]

    if user_classes := slide.frontmatter.get("class") or slide.frontmatter.get("cls"):
        classes.extend(user_classes.split())

    style = ""
    if slide.background:
        bg = slide.background
        if bg.startswith(("#", "rgb")):
            style = f"background-color: {bg};"
        else:
            url = _resolve_asset_url(bg)
            style = f"background-image: url('{url}'); background-size: cover; background-position: center;"

    if (cols := slide.frontmatter.get("cols")) and slide.layout == "grid":
        style += f" --grid-cols: {int(cols)};"

    image_url = slide.frontmatter.get("image")

    if slide.layout in _IMAGE_LAYOUTS and image_url:
        url = _resolve_asset_url(image_url)
        content = (
            f'<div class="slot-image" style="background-image: url(\'{url}\'); '
            f'background-size: cover; background-position: center;"></div>'
            f'<div class="slot-content">{slide.content}</div>'
        )
    else:
        content = slide.content

    return Div(
        NotStr(content),
        id=f"slide-{slide.index}",
        cls=" ".join(classes),
        style=style if style else None,
        data_slide_index=slide.index,
    )


def _grid_scaling_effect(root_cls: str):
    # CSS can't produce a unitless ratio from two lengths, so JS is needed
    return js(
        """
        if ($grid_open) {
            requestAnimationFrame(() => {
                const root = document.querySelector('.%s');
                const sw = parseFloat(getComputedStyle(root).getPropertyValue('--slide-width'));
                document.querySelectorAll('.grid-slide-card').forEach(card => {
                    const inner = card.querySelector('.grid-slide-inner');
                    if (inner) inner.style.transform = 'scale(' + (card.offsetWidth / sw) + ')';
                });
            });
        }
    """
        % root_cls
    )


def build_grid_cards(
    deck: Deck,
    slide_idx_signal,
    grid_open_signal,
    goto_url_fn: Callable[[int], str],
) -> list:
    return [
        Div(
            Div(render_slide(slide, deck), cls="grid-slide-inner"),
            Span(str(slide.index + 1), cls="grid-slide-number"),
            cls="grid-slide-card",
            data_class_current=slide_idx_signal == slide.index,
            data_on_click=[grid_open_signal.set(False), get(goto_url_fn(slide.index))],
        )
        for slide in deck.slides
    ]


def build_grid_modal(grid_cards: list, grid_open_signal, root_cls: str) -> Div:
    return Div(
        Div(*grid_cards, cls="grid-container"),
        cls="overview-grid-modal",
        data_class_active=grid_open_signal,
        data_on_click=js("if (evt.target === this) $grid_open = false"),
        data_effect=_grid_scaling_effect(root_cls),
    )


def create_presenter_view(deck: Deck, pres: "PresentationState", *, token: str = "", theme: str = "dark") -> Div:
    current_slide = pres.current_slide
    next_slide = pres.next_slide

    next_endpoint = "/api/presenter/next"
    prev_endpoint = "/api/presenter/prev"

    if token:
        canvas = DrawingCanvas(
            name="presenter_drawing",
            id="presenter-canvas",
            style="position:absolute;inset:0;width:100%;height:100%;z-index:100;",
            viewbox_width=VIEWBOX_WIDTH,
            viewbox_height=VIEWBOX_HEIGHT,
            theme=theme,
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
