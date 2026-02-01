"""Tests for stardeck renderer."""

from pathlib import Path

from stardeck.models import Deck, DeckConfig, SlideInfo
from stardeck.renderer import render_code_block, render_slide


def test_render_code_block():
    """render_code_block should highlight code with Pygments."""
    result = render_code_block("print('hi')", "python")
    result_str = str(result)
    assert "code-block" in result_str
    # Pygments adds syntax highlighting spans or classes


def test_render_code_block_no_language():
    """render_code_block should handle code without language."""
    result = render_code_block("hello world", "")
    result_str = str(result)
    assert "code-block" in result_str


def test_render_code_block_multiline():
    """render_code_block should handle multiline code."""
    code = """def hello():
    print("Hello")
    return True"""
    result = render_code_block(code, "python")
    result_str = str(result)
    assert "code-block" in result_str
    assert "def" in result_str or "hello" in result_str


def test_render_slide():
    """render_slide should wrap content with slide and layout classes."""
    slide = SlideInfo(
        content="<h1>Hi</h1>",
        raw="# Hi",
        index=0,
        start_line=0,
        end_line=1,
    )
    deck = Deck(
        slides=[slide],
        config=DeckConfig(),
        filepath=Path("test.md"),
        raw="# Hi",
    )
    result = render_slide(slide, deck)
    result_str = str(result)
    assert "slide-0" in result_str
    assert "layout-default" in result_str


def test_render_slide_with_layout():
    """render_slide should use layout from frontmatter."""
    slide = SlideInfo(
        content="<h1>Title</h1>",
        raw="# Title",
        index=0,
        start_line=0,
        end_line=1,
        frontmatter={"layout": "cover"},
    )
    deck = Deck(
        slides=[slide],
        config=DeckConfig(),
        filepath=Path("test.md"),
        raw="# Title",
    )
    result = render_slide(slide, deck)
    result_str = str(result)
    assert "layout-cover" in result_str


def test_render_slide_with_background():
    """render_slide should include background style."""
    slide = SlideInfo(
        content="<h1>Title</h1>",
        raw="# Title",
        index=0,
        start_line=0,
        end_line=1,
        frontmatter={"background": "./stars.jpg"},
    )
    deck = Deck(
        slides=[slide],
        config=DeckConfig(),
        filepath=Path("test.md"),
        raw="# Title",
    )
    result = render_slide(slide, deck)
    result_str = str(result)
    assert "stars.jpg" in result_str
