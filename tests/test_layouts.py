"""Tests for layouts, regions, and related frontmatter features."""

from pathlib import Path

from starhtml import to_xml

from stardeck.models import Deck, DeckConfig, SlideInfo
from stardeck.parser import transform_regions
from stardeck.renderer import render_slide


def _deck(slide):
    return Deck(slides=[slide], config=DeckConfig(), filepath=Path("t.md"), raw="")


def _slide(content="<h1>Hi</h1>", frontmatter=None, index=0):
    return SlideInfo(
        content=content,
        raw="",
        index=index,
        start_line=0,
        end_line=0,
        frontmatter=frontmatter or {},
    )


# --- class frontmatter ---


def test_class_frontmatter_applied():
    slide = _slide(frontmatter={"class": "text-center gap-8"})
    result = to_xml(render_slide(slide, _deck(slide)))
    assert "text-center" in result
    assert "gap-8" in result


def test_class_frontmatter_empty():
    slide = _slide(frontmatter={"class": ""})
    result = to_xml(render_slide(slide, _deck(slide)))
    assert "layout-default" in result


def test_class_frontmatter_none():
    """Empty class: in YAML produces None — should not crash or leak."""
    slide = _slide(frontmatter={"class": None})
    result = to_xml(render_slide(slide, _deck(slide)))
    assert "None" not in result
    assert "layout-default" in result


def test_cls_frontmatter_alias():
    """cls: should work as an alias for class: in frontmatter."""
    slide = _slide(frontmatter={"cls": "text-center gap-8"})
    result = to_xml(render_slide(slide, _deck(slide)))
    assert "text-center" in result
    assert "gap-8" in result


# --- transform_regions ---


def test_transform_regions_basic():
    content = "<left>\n\n## Hello\n\n</left>"
    result = transform_regions(content)
    assert 'data-region="left"' in result
    assert 'class="sd-region"' in result
    assert "## Hello" in result


def test_transform_regions_with_class():
    content = '<right class="p-4 text-center">\n\nContent\n\n</right>'
    result = transform_regions(content)
    assert 'data-region="right"' in result
    assert "p-4" in result
    assert "text-center" in result
    assert "sd-region" in result


def test_transform_regions_repeating():
    content = "<item>\n\nOne\n\n</item>\n<item>\n\nTwo\n\n</item>\n<item>\n\nThree\n\n</item>"
    result = transform_regions(content)
    assert result.count('data-region="item"') == 3


def test_transform_regions_skips_code_fences():
    content = "```html\n<left>\nfoo\n</left>\n```"
    result = transform_regions(content)
    assert "sd-region" not in result
    assert "<left>" in result


def test_transform_regions_with_click():
    content = "<left>\n\n<click>Reveal me</click>\n\n</left>"
    result = transform_regions(content)
    assert 'data-region="left"' in result
    assert "<click>Reveal me</click>" in result


def test_transform_regions_all_tag_names():
    for tag in ("left", "right", "top", "bottom", "main", "sidebar", "item", "step"):
        content = f"<{tag}>\n\nHello\n\n</{tag}>"
        result = transform_regions(content)
        assert f'data-region="{tag}"' in result


def test_transform_regions_unknown_tag_ignored():
    content = "<banana>\n\nHello\n\n</banana>"
    result = transform_regions(content)
    assert "sd-region" not in result


# --- image frontmatter ---


def test_render_image_layout():
    slide = _slide(
        content="<p>Description</p>",
        frontmatter={"layout": "image-right", "image": "assets/screenshot.png"},
    )
    result = to_xml(render_slide(slide, _deck(slide)))
    assert "slot-image" in result
    assert "slot-content" in result
    assert "screenshot.png" in result


def test_render_image_layout_no_image():
    slide = _slide(
        content="<p>Description</p>",
        frontmatter={"layout": "image-right"},
    )
    result = to_xml(render_slide(slide, _deck(slide)))
    assert "slot-image" not in result


def test_render_image_url_resolution():
    slide = _slide(
        content="<p>Hi</p>",
        frontmatter={"layout": "image-left", "image": "./assets/img.jpg"},
    )
    result = to_xml(render_slide(slide, _deck(slide)))
    assert "/assets/img.jpg" in result


def test_render_image_absolute_url():
    slide = _slide(
        content="<p>Hi</p>",
        frontmatter={"layout": "hero", "image": "https://example.com/img.jpg"},
    )
    result = to_xml(render_slide(slide, _deck(slide)))
    assert "https://example.com/img.jpg" in result


# --- grid cols ---


def test_grid_cols_custom_property():
    slide = _slide(
        content="<p>Items</p>",
        frontmatter={"layout": "grid", "cols": 3},
    )
    result = to_xml(render_slide(slide, _deck(slide)))
    assert "--grid-cols: 3" in result


# --- CSS class existence ---


def test_layout_css_classes_exist():
    css = Path(__file__).parent.parent / "stardeck/themes/default/styles.css"
    content = css.read_text()
    expected = [
        ".layout-cover",
        ".layout-default",
        ".layout-center",
        ".layout-section",
        ".layout-quote",
        ".layout-fact",
        ".layout-full",
        ".layout-two-cols",
        ".layout-image-left",
        ".layout-image-right",
        ".layout-hero",
        ".layout-caption",
        ".layout-statement",
        ".layout-three-cols",
        ".layout-sidebar-left",
        ".layout-sidebar-right",
        ".layout-comparison",
        ".layout-grid",
        ".layout-steps",
    ]
    for cls in expected:
        assert cls in content, f"Missing CSS class: {cls}"


# --- parse_deck integration ---


def test_parse_deck_regions_and_clicks(tmp_path):
    from stardeck.parser import parse_deck

    md = tmp_path / "slides.md"
    md.write_text(
        "---\nlayout: two-cols\n---\n"
        "<left>\n\n## Left\n\n</left>\n\n"
        "<right>\n\n<click>Reveal</click>\n\n</right>"
    )
    deck = parse_deck(md)
    slide = deck.slides[0]
    assert slide.layout == "two-cols"
    assert 'data-region="left"' in slide.content
    assert 'data-region="right"' in slide.content
    assert 'data-click="1"' in slide.content
