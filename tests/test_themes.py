"""Tests for the StarDeck theme system."""

import pytest
from stardeck.themes import deck_hdrs, get_theme_css, get_theme_metadata, list_themes


def test_get_theme_css_default_returns_css():
    css = get_theme_css("default")
    assert len(css) > 0


def test_get_theme_css_light_returns_css():
    css = get_theme_css("light")
    assert len(css) > 0
    assert "stardeck-root" in css


def test_get_theme_css_nonexistent_raises():
    with pytest.raises(FileNotFoundError):
        get_theme_css("nonexistent_theme_xyz")


def test_list_themes_includes_default():
    assert "default" in list_themes()


def test_list_themes_includes_light():
    assert "light" in list_themes()


def test_list_themes_returns_strings():
    themes = list_themes()
    assert isinstance(themes, list)
    assert all(isinstance(t, str) for t in themes)


def test_deck_hdrs_returns_header_elements():
    hdrs = deck_hdrs()
    assert isinstance(hdrs, list)
    assert len(hdrs) >= 1


def test_deck_hdrs_light_returns_header_elements():
    hdrs = deck_hdrs("light")
    assert isinstance(hdrs, list)
    assert len(hdrs) >= 1


def test_get_theme_metadata_default():
    meta = get_theme_metadata("default")
    assert meta["name"] == "default"
    assert isinstance(meta["description"], str)
    assert isinstance(meta["version"], str)


def test_get_theme_metadata_light():
    meta = get_theme_metadata("light")
    assert meta["name"] == "light"
    assert "light" in meta["description"].lower() or meta["description"]


def test_get_theme_metadata_nonexistent():
    meta = get_theme_metadata("nonexistent_theme_xyz")
    assert meta["name"] == "nonexistent_theme_xyz"
    assert meta["description"] == ""
    assert meta["version"] == "1.0.0"
