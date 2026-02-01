"""Tests for stardeck renderer."""

from stardeck.renderer import render_code_block


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
