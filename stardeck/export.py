"""Export a StarDeck presentation as standalone HTML."""

import html
import shutil
from importlib import resources
from pathlib import Path

from fastcore.xml import to_xml
from starhtml import Body, Button, Div, Head, Html, Meta, NotStr, Script, Signal, Span, Style, Title  # noqa: E501
from starhtml.datastar import js

from stardeck.parser import parse_deck
from stardeck.renderer import render_slide
from stardeck.themes import get_theme_css


def export_deck(deck_path: Path, output_dir: Path, theme: str = "default"):
    """Export a presentation to a self-contained directory."""
    deck = parse_deck(deck_path)
    theme_css = get_theme_css(theme)

    # Inline to avoid file:// CORS issues with ES modules
    datastar_js = (resources.files("starhtml") / "static" / "datastar.js").read_text()

    max_clicks_js = ", ".join(str(s.max_clicks) for s in deck.slides)

    _hash_nav_js = js(f"""
        const hash = window.location.hash;
        if (hash && hash.length > 1) {{
            const mc = [{max_clicks_js}];
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

    slide_divs = []
    for slide in deck.slides:
        # Hide non-first slides pre-Datastar to prevent flash (DS-001)
        hide = "display:none;" if slide.index > 0 else ""
        slide_divs.append(
            Div(
                render_slide(slide, deck),
                data_show=slide_index == slide.index,
                style=f"{hide}width:100%;height:100%",
            )
        )

    page = Html(
        Head(
            Meta(charset="UTF-8"),
            Meta(name="viewport", content="width=device-width, initial-scale=1.0"),
            Title(html.escape(deck.config.title)),
            Script(src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"),
            Script(datastar_js, type="module"),
            Style(theme_css),
        ),
        Body(
            Div(
                slide_index,
                Signal("clicks", 0),
                Signal("max_clicks", deck.slides[0].max_clicks if deck.slides else 0),
                (total_slides := Signal("total_slides", deck.total)),

                Div(
                    Div(*slide_divs, id="slide-content", style="width:100%;height:100%"),
                    cls="slide-viewport",
                ),

                Div(
                    Button(
                        NotStr("&larr;"), cls="nav-btn",
                        data_on_click=js(f"if ($slide_index > 0) {{ $clicks = 0; $slide_index--; $max_clicks = [{max_clicks_js}][$slide_index]; }}"),
                        data_attr_disabled=slide_index == 0,
                    ),
                    Span(data_text=slide_index + 1 + " / " + total_slides, cls="slide-counter"),
                    Button(
                        NotStr("&rarr;"), cls="nav-btn",
                        data_on_click=js(f"if ($slide_index < $total_slides - 1) {{ $clicks = 0; $slide_index++; $max_clicks = [{max_clicks_js}][$slide_index]; }}"),
                        data_attr_disabled=slide_index == total_slides - 1,
                    ),
                    cls="navigation-bar",
                ),

                Span(
                    data_on_keydown=(
                        js(f"""
                        const mc = [{max_clicks_js}];
                        if (evt.key === 'ArrowRight' || evt.key === ' ') {{
                            evt.preventDefault();
                            if ($clicks < $max_clicks) {{
                                $clicks++;
                            }} else if ($slide_index < $total_slides - 1) {{
                                $clicks = 0;
                                $slide_index++;
                                $max_clicks = mc[$slide_index];
                            }}
                        }} else if (evt.key === 'ArrowLeft') {{
                            evt.preventDefault();
                            if ($clicks > 0) {{
                                $clicks--;
                            }} else if ($slide_index > 0) {{
                                $slide_index--;
                                $max_clicks = mc[$slide_index];
                                $clicks = $max_clicks;
                            }}
                        }}
                        """),
                        {"window": True},
                    ),
                    style="display:none",
                ),

                Span(
                    data_on_load=_hash_nav_js,
                    style="display:none",
                ),

                Span(
                    data_on_hashchange=(_hash_nav_js, {"window": True}),
                    style="display:none",
                ),

                Span(
                    data_effect=js("window.history.replaceState(null, '', '#' + ($slide_index + 1) + ($clicks > 0 ? '.' + $clicks : ''));"),
                    style="display:none",
                ),

                cls="stardeck-root",
            ),
        ),
        lang="en",
    )

    index_html = "<!DOCTYPE html>\n" + to_xml(page)

    # Rewrite absolute /assets/ paths to relative for file:// compatibility
    index_html = index_html.replace("url('/assets/", "url('assets/")
    index_html = index_html.replace('url("/assets/', 'url("assets/')
    index_html = index_html.replace('src="/assets/', 'src="assets/')

    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "index.html").write_text(index_html)

    assets_dir = deck_path.parent / "assets"
    if assets_dir.is_dir():
        dest_assets = output_dir / "assets"
        if dest_assets.exists():
            shutil.rmtree(dest_assets)
        shutil.copytree(assets_dir, dest_assets)

    return output_dir
