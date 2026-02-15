"""Tests for the StarDeck server module."""

from pathlib import Path

from starlette.testclient import TestClient

from .conftest import mk_deck, parse_sse_signals


def test_create_app(tmp_path: Path):
    """Test that create_app returns app, rt, and deck_state tuple."""
    from stardeck.server import create_app

    md_file = mk_deck(tmp_path, "# Test Slide")
    app, rt, deck_state = create_app(md_file)

    assert deck_state["deck"].total == 1
    assert app is not None
    assert rt is not None


def test_next_slide_endpoint(client: TestClient):
    """Advancing from slide 0 yields slide_index == 1."""
    response = client.get("/api/slide/next?slide_index=0")
    sigs = parse_sse_signals(response.text)
    assert sigs["slide_index"] == 1


def test_prev_slide_endpoint(client: TestClient):
    """Going prev from slide 2 yields slide_index == 1."""
    response = client.get("/api/slide/prev?slide_index=2")
    sigs = parse_sse_signals(response.text)
    assert sigs["slide_index"] == 1


def test_goto_slide_endpoint(client: TestClient):
    """Goto slide 2 yields slide_index == 2."""
    response = client.get("/api/slide/2")
    sigs = parse_sse_signals(response.text)
    assert sigs["slide_index"] == 2


def test_reload_endpoint(client: TestClient):
    """Reload returns SSE with re-parsed deck."""
    response = client.get("/api/reload")
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]


def test_watch_creates_relay(tmp_path: Path):
    from stardeck.server import create_app

    md_file = mk_deck(tmp_path, "# Test Slide")
    _app, _rt, deck_state = create_app(md_file, watch=True)
    assert "watch_relay" in deck_state


def test_watch_home_has_sse_elements(tmp_path: Path):
    from stardeck.server import create_app

    md_file = mk_deck(tmp_path, "# Test Slide")
    app, _rt, _state = create_app(md_file, watch=True)
    html = TestClient(app).get("/").text
    assert "file_version" in html
    assert "watch-events" in html


def test_watch_disabled_no_sse_elements(tmp_path: Path):
    from stardeck.server import create_app

    md_file = mk_deck(tmp_path, "# Test Slide")
    app, _rt, _state = create_app(md_file, watch=False)
    html = TestClient(app).get("/").text
    assert "file_version" not in html
    assert "watch-events" not in html


def test_watch_events_disabled_without_watch(tmp_path: Path):
    from stardeck.server import create_app

    md_file = mk_deck(tmp_path, "# Test Slide")
    app, _rt, _state = create_app(md_file, watch=False)
    response = TestClient(app).get("/api/watch-events")
    assert response.status_code == 404


def test_home_has_clicks_signal(client: TestClient):
    html = client.get("/").text
    assert "clicks" in html
    assert "data-signals" in html


def test_keyboard_navigation_with_clicks(client: TestClient):
    html = client.get("/").text
    assert "$clicks<$max_clicks" in html or "$clicks < $max_clicks" in html


def test_next_slide_resets_clicks(client: TestClient):
    """Next slide SSE response has clicks == 0."""
    sigs = parse_sse_signals(client.get("/api/slide/next?slide_index=0").text)
    assert sigs["clicks"] == 0


def test_prev_slide_resets_clicks(client: TestClient):
    """Prev from slide 2 yields slide_index 1, clicks 0."""
    sigs = parse_sse_signals(client.get("/api/slide/prev?slide_index=2").text)
    assert sigs["slide_index"] == 1
    assert sigs["clicks"] == 0


def test_goto_slide_resets_clicks(client: TestClient):
    """Goto slide 1 resets clicks to 0."""
    sigs = parse_sse_signals(client.get("/api/slide/1").text)
    assert sigs["clicks"] == 0


def test_url_hash_effect_present(client: TestClient):
    """Hash update effect JS is present in home page."""
    html = client.get("/").text
    assert "history.replaceState" in html
    assert "$clicks" in html


def test_goto_slide_accepts_clicks_param(client: TestClient):
    """Goto with clicks param passes the value through."""
    sigs = parse_sse_signals(client.get("/api/slide/1?clicks=0").text)
    assert sigs["clicks"] == 0


def test_goto_slide_clamps_clicks_to_max(tmp_path: Path):
    """Clicks are clamped to max_clicks for the target slide."""
    from stardeck.server import create_app

    md_file = mk_deck(tmp_path, "# Slide 1\n<click>A</click>\n---\n# Slide 2")
    app, _rt, _state = create_app(md_file)
    sigs = parse_sse_signals(TestClient(app).get("/api/slide/0?clicks=100").text)
    assert sigs["clicks"] == 1  # max_clicks for slide 0 is 1


def test_server_uses_motion_for_click_reveals(tmp_path: Path):
    """Server-rendered slides use computed Signal + data-motion visibility."""
    from stardeck.server import create_app

    md_file = mk_deck(tmp_path, "# Slide\n<click>Reveal</click>")
    app, _rt, _state = create_app(md_file)
    html = TestClient(app).get("/").text
    assert "data-motion=" in html
    assert "type:visibility" in html
    # Computed signal defined at page level by Signal("vis1", clicks >= 1)
    assert "data-computed:vis1" in html
    assert "signal:$vis1" in html


def test_motion_plugin_not_loaded_without_clicks(tmp_path: Path):
    """Decks without <click> tags should not load the motion plugin JS."""
    from stardeck.server import create_app

    md_file = mk_deck(tmp_path, "# Slide 1\n---\n# Slide 2")
    app, _rt, _state = create_app(md_file)
    html = TestClient(app).get("/").text
    assert "data-motion=" not in html
    assert "data-computed:vis" not in html


def test_server_hide_uses_css_approach(tmp_path: Path):
    """Decks with <click hide> use CSS opacity transitions, not data-motion."""
    from stardeck.server import create_app

    md_file = mk_deck(tmp_path, "# Slide\n<click hide>Gone</click>\n<click>Show</click>")
    app, _rt, _state = create_app(md_file)
    html = TestClient(app).get("/").text
    assert "click-hide" in html
    assert "data-class:click-hidden" in html


def test_server_range_signal(tmp_path: Path):
    """Decks with at= ranges produce vis_N_M computed signals."""
    from stardeck.server import create_app

    md_file = mk_deck(tmp_path, '# Slide\n<click at="2-4">Temp</click>')
    app, _rt, _state = create_app(md_file)
    html = TestClient(app).get("/").text
    assert "data-computed:vis_2_4" in html


def test_server_detects_after_tag(tmp_path: Path):
    """Decks with only <after> tags still load motion plugin."""
    from stardeck.server import create_app

    md_file = mk_deck(tmp_path, "# Slide\n<click>A</click>\n<after>B</after>")
    app, _rt, _state = create_app(md_file)
    html = TestClient(app).get("/").text
    assert "data-motion=" in html


def test_server_detects_clicks_wrapper(tmp_path: Path):
    """Decks with <clicks> wrapper load motion plugin."""
    from stardeck.server import create_app

    md_file = mk_deck(tmp_path, "# Slide\n<clicks>\n\nA\n\nB\n\n</clicks>")
    app, _rt, _state = create_app(md_file)
    html = TestClient(app).get("/").text
    assert "data-motion=" in html
