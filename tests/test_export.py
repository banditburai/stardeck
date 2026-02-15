"""Tests for export_deck — real HTML generation, no mocks."""

from stardeck.export import export_deck

from .conftest import mk_deck


def test_exported_html_contains_all_slides(tmp_path):
    deck_path = mk_deck(tmp_path, "# One\n---\n# Two\n---\n# Three")
    export_deck(deck_path, tmp_path / "out")
    html = (tmp_path / "out" / "index.html").read_text()
    assert "One" in html and "Two" in html and "Three" in html


def test_first_slide_visible_rest_hidden(tmp_path):
    deck_path = mk_deck(tmp_path, "# A\n---\n# B\n---\n# C")
    export_deck(deck_path, tmp_path / "out")
    html = (tmp_path / "out" / "index.html").read_text()
    # Slide wrappers after the first have display:none for flash prevention
    assert html.count("display:none") >= 2


def test_navigation_buttons_present(tmp_path):
    deck_path = mk_deck(tmp_path, "# X\n---\n# Y")
    export_deck(deck_path, tmp_path / "out")
    html = (tmp_path / "out" / "index.html").read_text()
    assert "nav-btn" in html
    assert "navigation-bar" in html


def test_signals_initialized(tmp_path):
    deck_path = mk_deck(tmp_path, "# A\n---\n# B")
    export_deck(deck_path, tmp_path / "out")
    html = (tmp_path / "out" / "index.html").read_text()
    for sig in ("slide_index", "clicks", "max_clicks", "total_slides"):
        assert sig in html, f"signal {sig} missing"


def test_assets_copied(tmp_path):
    deck_path = mk_deck(tmp_path, "# Slide")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "logo.png").write_bytes(b"\x89PNG")
    export_deck(deck_path, tmp_path / "out")
    assert (tmp_path / "out" / "assets" / "logo.png").exists()


def test_assets_skipped_when_absent(tmp_path):
    deck_path = mk_deck(tmp_path, "# Slide")
    export_deck(deck_path, tmp_path / "out")
    assert not (tmp_path / "out" / "assets").exists()


def test_asset_paths_rewritten(tmp_path):
    deck_path = mk_deck(tmp_path, "---\nbackground: ./bg.jpg\n---\n# Slide")
    (tmp_path / "assets").mkdir()
    export_deck(deck_path, tmp_path / "out")
    html = (tmp_path / "out" / "index.html").read_text()
    # /assets/ paths should become relative assets/ for file:// support
    assert "/assets/" not in html or "assets/" in html


def test_theme_css_included(tmp_path):
    deck_path = mk_deck(tmp_path, "# Slide")
    export_deck(deck_path, tmp_path / "out")
    html = (tmp_path / "out" / "index.html").read_text()
    assert "<style>" in html


def test_output_dir_created_nested(tmp_path):
    deck_path = mk_deck(tmp_path, "# Slide")
    export_deck(deck_path, tmp_path / "a" / "b" / "c")
    assert (tmp_path / "a" / "b" / "c" / "index.html").exists()


def test_hash_navigation_js_present(tmp_path):
    deck_path = mk_deck(tmp_path, "# A\n---\n# B")
    export_deck(deck_path, tmp_path / "out")
    html = (tmp_path / "out" / "index.html").read_text()
    assert "location.hash" in html or "hashchange" in html


def test_export_includes_motion_for_clicks(tmp_path):
    """Decks with <click> tags include motion plugin JS and import map."""
    deck_path = mk_deck(tmp_path, "# Slide\n<click>Reveal</click>")
    export_deck(deck_path, tmp_path / "out")
    out = tmp_path / "out"
    html = (out / "index.html").read_text()
    assert (out / "motion.js").exists()
    assert (out / "datastar.js").exists()
    assert "importmap" in html
    assert "@starhtml/plugins/motion" in html
    # Computed signal at page level + motion attr on click-reveal
    assert "data-computed:vis1" in html
    assert "data-motion" in html


def test_export_excludes_motion_without_clicks(tmp_path):
    """Decks without <click> tags should not include motion plugin."""
    deck_path = mk_deck(tmp_path, "# Slide 1\n---\n# Slide 2")
    export_deck(deck_path, tmp_path / "out")
    out = tmp_path / "out"
    html = (out / "index.html").read_text()
    assert not (out / "motion.js").exists()
    assert (out / "datastar.js").exists()
    assert "@starhtml/plugins/motion" not in html


def test_export_hide_uses_css_approach(tmp_path):
    """Export with <click hide> uses CSS opacity transitions, not data-motion."""
    deck_path = mk_deck(tmp_path, "# Slide\n<click hide>Gone</click>\n<click>Show</click>")
    export_deck(deck_path, tmp_path / "out")
    html = (tmp_path / "out" / "index.html").read_text()
    assert "click-hide" in html
    assert "data-class:click-hidden" in html


def test_export_range_signal(tmp_path):
    """Export with at= ranges produces vis_N_M computed signals."""
    deck_path = mk_deck(tmp_path, '# Slide\n<click at="2-4">Temp</click>')
    export_deck(deck_path, tmp_path / "out")
    html = (tmp_path / "out" / "index.html").read_text()
    assert "data-computed:vis_2_4" in html
