"""Export a StarDeck presentation as standalone HTML."""

import json
import re
import shutil
from importlib import resources
from pathlib import Path

from fastcore.xml import to_xml
from starhtml import Body, Button, Div, Head, Html, Meta, NotStr, Script, Signal, Span, Style, Title
from starhtml.datastar import evt, js, seq

from stardeck.parser import build_click_signals, deck_has_clicks, parse_deck
from stardeck.renderer import HASH_UPDATE_EFFECT, render_slide
from stardeck.themes import deck_hdrs

_MOTION_CRITICAL_CSS = "[data-motion]:not([data-motion-ready]){opacity:0}"
_MOTION_LOADER = (
    "import{attribute,action}from'datastar';\n"
    "import plugin_0,{motionActionPlugin,motionExitAttributePlugin}from'@starhtml/plugins/motion';\n"
    "attribute(motionExitAttributePlugin);\n"
    "attribute(plugin_0);\n"
    "action(motionActionPlugin);"
)


def _write_js_assets(output_dir: Path, *, include_motion: bool) -> None:
    """Write JS files to output directory for import map resolution."""
    datastar_js = (resources.files("starhtml") / "static" / "datastar.js").read_text()
    (output_dir / "datastar.js").write_text(datastar_js)

    if include_motion:
        motion_js = (resources.files("starhtml") / "static" / "js" / "plugins" / "motion.js").read_text()
        (output_dir / "motion.js").write_text(motion_js)


def _build_head(deck, theme: str, *, use_motion: bool) -> Head:
    import_map = {"datastar": "./datastar.js"}
    if use_motion:
        import_map["@starhtml/plugins/motion"] = "./motion.js"

    head_children = [
        Meta(charset="UTF-8"),
        Meta(name="viewport", content="width=device-width, initial-scale=1.0"),
        Title(deck.config.title),
        # Import map MUST precede any type="module" scripts
        NotStr(f'<script type="importmap">{json.dumps({"imports": import_map})}</script>'),
        *deck_hdrs(theme),
        Script(src="./datastar.js", type="module"),
    ]
    if use_motion:
        head_children.append(Style(_MOTION_CRITICAL_CSS))
        head_children.append(Script(_MOTION_LOADER, type="module"))

    return Head(*head_children)


def export_deck(deck_path: Path, output_dir: Path, theme: str = "default") -> Path:
    """Export a presentation to a self-contained directory."""
    use_motion = deck_has_clicks(deck_path)
    deck = parse_deck(deck_path, use_motion=use_motion)

    mc_array = f"[{', '.join(str(s.max_clicks) for s in deck.slides)}]"

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

    vis_signals = build_click_signals(deck, clicks)

    is_right = (evt.key == "ArrowRight") | (evt.key == " ")
    is_left = evt.key == "ArrowLeft"

    # if/else prevents the sequential-if bug where the second condition
    # re-evaluates after the first mutates $clicks, skipping a click state.
    fwd_nav = js(f"""
        if ($clicks < $max_clicks) $clicks++;
        else if ($slide_index < $total_slides - 1) {{
            $clicks = 0; $slide_index++; $max_clicks = {mc_array}[$slide_index];
        }}
    """)
    back_nav = js(f"""
        if ($clicks > 0) $clicks--;
        else if ($slide_index > 0) {{
            $slide_index--; $max_clicks = {mc_array}[$slide_index]; $clicks = $max_clicks;
        }}
    """)

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
        _build_head(deck, theme, use_motion=use_motion),
        Body(
            Div(
                slide_index,
                clicks,
                max_clicks,
                total_slides,
                *vis_signals,
                Div(
                    Div(*slide_divs, id="slide-content", style="width:100%;height:100%"),
                    cls="slide-viewport",
                ),
                Div(
                    Button("←", cls="nav-btn", data_on_click=back_nav, data_attr_disabled=slide_index == 0),
                    Span(f"1 / {deck.total}", data_text=slide_index + 1 + " / " + total_slides, cls="slide-counter"),
                    Button("→", cls="nav-btn", data_on_click=fwd_nav, data_attr_disabled=slide_index == total_slides - 1),
                    cls="navigation-bar",
                ),
                Span(
                    data_on_keydown=(
                        [
                            is_right.then(seq(evt.preventDefault(), fwd_nav)),
                            is_left.then(seq(evt.preventDefault(), back_nav)),
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
    _write_js_assets(output_dir, include_motion=use_motion)

    assets_dir = deck_path.parent / "assets"
    if assets_dir.is_dir():
        dest_assets = output_dir / "assets"
        if dest_assets.exists():
            shutil.rmtree(dest_assets)
        shutil.copytree(assets_dir, dest_assets)

    return output_dir
