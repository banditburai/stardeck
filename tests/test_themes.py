"""Tests for the StarDeck theme system."""

import pytest
from stardeck.themes import deck_hdrs, get_theme_css, list_themes


def test_get_theme_css_default_returns_css():
    css = get_theme_css("default")
    assert len(css) > 0


def test_get_theme_css_nonexistent_raises():
    with pytest.raises(FileNotFoundError):
        get_theme_css("nonexistent_theme_xyz")


def test_list_themes_includes_default():
    assert "default" in list_themes()


def test_list_themes_returns_strings():
    themes = list_themes()
    assert isinstance(themes, list)
    assert all(isinstance(t, str) for t in themes)


def test_deck_hdrs_returns_header_elements():
    hdrs = deck_hdrs()
    assert isinstance(hdrs, list)
    assert len(hdrs) >= 1
