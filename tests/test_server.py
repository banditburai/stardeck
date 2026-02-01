"""Tests for the StarDeck server module."""

from pathlib import Path


def test_create_app(tmp_path: Path):
    """Test that create_app returns app, rt, and deck tuple."""
    from stardeck.server import create_app

    md_file = tmp_path / "slides.md"
    md_file.write_text("# Test Slide")

    app, rt, deck = create_app(md_file)

    assert deck.total == 1
    assert app is not None
    assert rt is not None
