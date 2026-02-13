"""Tests for stardeck renderer."""

from starhtml import to_xml

from stardeck.models import Deck, DeckConfig, SlideInfo
from stardeck.renderer import render_code_block, render_slide


def _slide(content="<h1>Hi</h1>", index=0, frontmatter=None):
    return SlideInfo(content=content, index=index, frontmatter=frontmatter or {})


def _deck(slide, **config_kw):
    return Deck(slides=[slide], config=DeckConfig(**config_kw))


def _render(slide, **config_kw):
    return to_xml(render_slide(slide, _deck(slide, **config_kw)))


def test_render_code_block():
    result_str = str(render_code_block("print('hi')", "python"))
    assert "code-block" in result_str


def test_render_code_block_no_language():
    result_str = str(render_code_block("hello world", ""))
    assert "code-block" in result_str


def test_render_code_block_multiline():
    code = 'def hello():\n    print("Hello")\n    return True'
    result_str = str(render_code_block(code, "python"))
    assert "code-block" in result_str
    assert "def" in result_str or "hello" in result_str


def test_render_slide():
    result = _render(_slide())
    assert "slide-0" in result
    assert "layout-default" in result


def test_render_slide_with_layout():
    result = _render(_slide(frontmatter={"layout": "cover"}))
    assert "layout-cover" in result


def test_render_slide_with_background_image():
    result = _render(_slide(content="<h1>Title</h1>", frontmatter={"background": "./stars.jpg"}))
    assert "background-image" in result
    assert "stars.jpg" in result


def test_render_slide_with_background_color():
    result = _render(_slide(content="<h1>Title</h1>", frontmatter={"background": "#2563eb"}))
    assert "background-color" in result
    assert "#2563eb" in result


def test_render_slide_has_id():
    result = _render(_slide(index=3))
    assert 'id="slide-3"' in result


def test_render_slide_has_data_slide_index():
    result = _render(_slide(index=5))
    assert 'data-slide-index="5"' in result


def test_render_slide_has_transition_class():
    result = _render(_slide(frontmatter={"transition": "slide-left"}))
    assert "transition-slide-left" in result


def test_render_slide_uses_deck_transition_fallback():
    result = _render(_slide(), transition="zoom")
    assert "transition-zoom" in result


def test_render_slide_transition_slide_right():
    result = _render(_slide(frontmatter={"transition": "slide-right"}))
    assert "transition-slide-right" in result


def test_render_slide_transition_slide_up():
    result = _render(_slide(frontmatter={"transition": "slide-up"}))
    assert "transition-slide-up" in result


def test_render_slide_transition_slide_down():
    result = _render(_slide(frontmatter={"transition": "slide-down"}))
    assert "transition-slide-down" in result
