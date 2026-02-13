"""Export a StarDeck presentation as standalone HTML."""

import re
import shutil
from importlib import resources
from pathlib import Path

from fastcore.xml import to_xml
from starhtml import Body, Button, Div, Head, Html, Meta, Script, Signal, Span, Title
from starhtml.datastar import evt, expr, js, seq

from stardeck.parser import parse_deck
from stardeck.renderer import HASH_UPDATE_EFFECT, render_slide
from stardeck.themes import deck_hdrs


def export_deck(deck_path: Path, output_dir: Path, theme: str = "default") -> Path:
    """Export a presentation to a self-contained directory."""
    deck = parse_deck(deck_path)

    # Inline to avoid file:// CORS issues with ES modules
    datastar_js = (resources.files("starhtml") / "static" / "datastar.js").read_text()

    mc_array = f"[{', '.join(str(s.max_clicks) for s in deck.slides)}]"
    mc = expr([s.max_clicks for s in deck.slides])

    hash_nav_js = js(f"""
        const hash = window.location.hash;
        if (hash && hash.length > 1) {{
            const mc = {mc_array};
            const parts = hash.substring(1).split('.');
            const slideNum = parseInt(parts[0], 10);
            const clickNum = parts.length > 1 ? parseInt(parts[1], 10) : 0;
            if (!isNaN(slideNum) && slideNum >= 1 && slideNum <= {deck.total}) {{
                $slide_index = slideNum - 1;
                $max_clicks = mc[$slide_index];
                $clicks = Math.min(clickNum, $max_clicks);
            }}
        }}
    """)

    slide_index = Signal("slide_index", 0)
    clicks = Signal("clicks", 0)
    max_clicks = Signal("max_clicks", deck.slides[0].max_clicks if deck.slides else 0)
    total_slides = Signal("total_slides", deck.total)

    is_right = (evt.key == "ArrowRight") | (evt.key == " ")
    is_left = evt.key == "ArrowLeft"
    can_click_fwd = clicks < max_clicks
    can_slide_fwd = slide_index < total_slides - 1
    can_click_back = clicks > 0
    can_slide_back = slide_index > 0

    # Hide non-first slides pre-Datastar to prevent flash (DS-001)
    slide_divs = [
        Div(
            render_slide(slide, deck),
            data_show=slide_index == slide.index,
            style=f"{'display:none;' if slide.index > 0 else ''}width:100%;height:100%",
        )
        for slide in deck.slides
    ]

    page = Html(
        Head(
            Meta(charset="UTF-8"),
            Meta(name="viewport", content="width=device-width, initial-scale=1.0"),
            Title(deck.config.title),
            *deck_hdrs(theme),
            Script(datastar_js, type="module"),
        ),
        Body(
            Div(
                slide_index,
                clicks,
                max_clicks,
                total_slides,

                Div(
                    Div(*slide_divs, id="slide-content", style="width:100%;height:100%"),
                    cls="slide-viewport",
                ),

                Div(
                    Button(
                        "←", cls="nav-btn",
                        data_on_click=[
                            can_click_back.then(clicks.sub(1)),
                            (~can_click_back & can_slide_back).then(
                                seq(slide_index.sub(1), max_clicks.set(mc[slide_index]), clicks.set(max_clicks))
                            ),
                        ],
                        data_attr_disabled=slide_index == 0,
                    ),
                    Span(
                        f"1 / {deck.total}",
                        data_text=slide_index + 1 + " / " + total_slides,
                        cls="slide-counter",
                    ),
                    Button(
                        "→", cls="nav-btn",
                        data_on_click=[
                            can_click_fwd.then(clicks.add(1)),
                            (~can_click_fwd & can_slide_fwd).then(
                                seq(clicks.set(0), slide_index.add(1), max_clicks.set(mc[slide_index]))
                            ),
                        ],
                        data_attr_disabled=slide_index == total_slides - 1,
                    ),
                    cls="navigation-bar",
                ),

                Span(
                    data_on_keydown=(
                        [
                            is_right.then(evt.preventDefault()),
                            (is_right & can_click_fwd).then(clicks.add(1)),
                            (is_right & ~can_click_fwd & can_slide_fwd).then(
                                seq(clicks.set(0), slide_index.add(1), max_clicks.set(mc[slide_index]))
                            ),
                            is_left.then(evt.preventDefault()),
                            (is_left & can_click_back).then(clicks.sub(1)),
                            (is_left & ~can_click_back & can_slide_back).then(
                                seq(slide_index.sub(1), max_clicks.set(mc[slide_index]), clicks.set(max_clicks))
                            ),
                        ],
                        {"window": True},
                    ),
                    style="display:none",
                ),

                Span(data_on_load=hash_nav_js, style="display:none"),
                Span(data_on_hashchange=(hash_nav_js, {"window": True}), style="display:none"),
                Span(data_effect=HASH_UPDATE_EFFECT, style="display:none"),

                cls="stardeck-root",
            ),
        ),
        lang="en",
    )

    index_html = "<!DOCTYPE html>\n" + to_xml(page)

    # file:// needs relative asset paths
    index_html = re.sub(r"""((?:url\(|src=|srcset=)['"]?)/assets/""", r"\1assets/", index_html)

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "index.html").write_text(index_html)

    assets_dir = deck_path.parent / "assets"
    if assets_dir.is_dir():
        dest_assets = output_dir / "assets"
        if dest_assets.exists():
            shutil.rmtree(dest_assets)
        shutil.copytree(assets_dir, dest_assets)

    return output_dir
