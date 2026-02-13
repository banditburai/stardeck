"""Rendering utilities for StarDeck."""

from collections.abc import Callable

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import get_lexer_by_name, guess_lexer
from starhtml import Code, Div, NotStr, Pre, Span, get
from starhtml.datastar import js

from stardeck.models import Deck, SlideInfo

SLIDE_WIDTH = 1920
SLIDE_HEIGHT = 1080
VIEWBOX_WIDTH = 160
VIEWBOX_HEIGHT = 90

HASH_UPDATE_EFFECT = js(
    "window.history.replaceState(null, '', '#' + ($slide_index + 1) + ($clicks > 0 ? '.' + $clicks : ''))"
)


def _resolve_asset_url(raw: str) -> str:
    if raw.startswith(("http://", "https://", "/", "data:")):
        return raw
    if raw.startswith("./"):
        return raw[1:]
    return f"/{raw}"


def render_code_block(code: str, language: str = "") -> Div:
    try:
        lexer = get_lexer_by_name(language) if language else guess_lexer(code)
    except Exception:
        from pygments.lexers import TextLexer

        lexer = TextLexer()

    formatter = HtmlFormatter(nowrap=True, cssclass="highlight")
    highlighted = highlight(code, lexer, formatter)

    return Div(
        Pre(Code(NotStr(highlighted))),
        cls="code-block",
    )


def render_slide(slide: SlideInfo, deck: Deck) -> Div:
    transition = slide.frontmatter.get("transition") or deck.config.transition

    classes = [
        f"slide-{slide.index}",
        f"layout-{slide.layout}",
        f"transition-{transition}",
        "slide",
    ]

    user_classes = slide.frontmatter.get("class") or slide.frontmatter.get("cls") or ""
    if user_classes:
        classes.extend(user_classes.split())

    style = ""
    if slide.background:
        bg = slide.background
        if bg.startswith(("#", "rgb")):
            style = f"background-color: {bg};"
        else:
            url = _resolve_asset_url(bg)
            style = f"background-image: url('{url}'); background-size: cover; background-position: center;"

    cols = slide.frontmatter.get("cols")
    if cols and slide.layout == "grid":
        style += f" --grid-cols: {int(cols)};"

    image_layouts = {"image-left", "image-right", "hero", "caption"}
    image_url = slide.frontmatter.get("image", "")

    if slide.layout in image_layouts and image_url:
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
