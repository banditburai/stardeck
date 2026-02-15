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


# --- Presenter endpoints ---


def test_presenter_next_endpoint(tmp_path: Path):
    from stardeck.server import create_app

    md_file = mk_deck(tmp_path, "# S1\n---\n# S2\n---\n# S3")
    app, _rt, state = create_app(md_file)
    client = TestClient(app)
    resp = client.get("/api/presenter/next")
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]
    assert state["presentation"].slide_index == 1


def test_presenter_prev_endpoint(tmp_path: Path):
    from stardeck.server import create_app

    md_file = mk_deck(tmp_path, "# S1\n---\n# S2\n---\n# S3")
    app, _rt, state = create_app(md_file)
    pres = state["presentation"]
    pres.slide_index = 2
    resp = TestClient(app).get("/api/presenter/prev")
    assert resp.status_code == 200
    assert pres.slide_index == 1


def test_presenter_goto_endpoint(tmp_path: Path):
    from stardeck.server import create_app

    md_file = mk_deck(tmp_path, "# S1\n---\n# S2\n---\n# S3")
    app, _rt, state = create_app(md_file)
    resp = TestClient(app).get("/api/presenter/goto/2")
    assert resp.status_code == 200
    assert state["presentation"].slide_index == 2


def test_presenter_changes_unauthorized(tmp_path: Path):
    from stardeck.server import create_app

    md_file = mk_deck(tmp_path, "# S1")
    app, _rt, _state = create_app(md_file)
    resp = TestClient(app).post("/api/presenter/changes?token=wrong", json={"changes": []})
    assert resp.status_code == 401


def test_presenter_changes_invalid_json(tmp_path: Path):
    from stardeck.server import create_app

    md_file = mk_deck(tmp_path, "# S1")
    app, _rt, state = create_app(md_file)
    token = state["presenter_token"]
    resp = TestClient(app).post(
        f"/api/presenter/changes?token={token}",
        content=b"not json",
        headers={"content-type": "application/json"},
    )
    assert resp.status_code == 400


def test_presenter_changes_applies_drawing(tmp_path: Path):
    from stardeck.server import create_app

    md_file = mk_deck(tmp_path, "# S1")
    app, _rt, state = create_app(md_file)
    token = state["presenter_token"]
    changes = [{"type": "path", "data": "M0,0 L10,10"}]
    resp = TestClient(app).post(
        f"/api/presenter/changes?token={token}",
        json={"changes": changes, "slide_index": 0},
    )
    assert resp.status_code == 200
    assert resp.json()["applied"] == 1


# --- Yield presenter updates ---


def test_yield_presenter_updates_emits_signals(tmp_path: Path):
    from stardeck.parser import parse_deck
    from stardeck.server import yield_presenter_updates

    md_file = mk_deck(tmp_path, "# S1\n---\n# S2")
    deck = parse_deck(md_file)
    events = list(yield_presenter_updates(deck, 0))
    assert len(events) >= 3  # signals + current slide + next slide + notes


def test_yield_presenter_updates_last_slide(tmp_path: Path):
    """At last slide, next preview shows 'End of presentation'."""
    from fastcore.xml import to_xml
    from stardeck.parser import parse_deck
    from stardeck.server import yield_presenter_updates

    md_file = mk_deck(tmp_path, "# Only")
    deck = parse_deck(md_file)
    events = list(yield_presenter_updates(deck, 0))
    html = "".join(to_xml(e) if hasattr(e, '__ft__') else str(e) for e in events)
    assert "End of presentation" in html


def test_yield_presenter_updates_with_snapshot(tmp_path: Path):
    from stardeck.parser import parse_deck
    from stardeck.server import yield_presenter_updates

    md_file = mk_deck(tmp_path, "# S1")
    deck = parse_deck(md_file)
    snapshot = [{"type": "path", "data": "M0,0"}]
    events = list(yield_presenter_updates(deck, 0, drawing_snapshot=snapshot))
    # Should include the drawing script event
    assert len(events) >= 4


# --- PresentationState boundary ---


def test_presentation_state_next_slide_at_end(tmp_path: Path):
    from stardeck.parser import parse_deck
    from stardeck.server import PresentationState

    md_file = mk_deck(tmp_path, "# Only")
    deck = parse_deck(md_file)
    pres = PresentationState(deck)
    assert pres.next_slide is None


def test_presentation_state_next_slide_exists(tmp_path: Path):
    from stardeck.parser import parse_deck
    from stardeck.server import PresentationState

    md_file = mk_deck(tmp_path, "# S1\n---\n# S2")
    deck = parse_deck(md_file)
    pres = PresentationState(deck)
    assert pres.next_slide is not None
    assert pres.next_slide.index == 1


# --- Reload with signal dependency change ---


def test_reload_triggers_page_reload_on_new_clicks(tmp_path: Path):
    """When reloaded deck has more click signals, force full page reload."""
    from stardeck.server import create_app

    md_file = mk_deck(tmp_path, "# S1")
    app, _rt, state = create_app(md_file)
    client = TestClient(app)

    # Rewrite file to have clicks (increases max_clicks)
    md_file.write_text("# S1\n<click>A</click>\n<click>B</click>")
    resp = client.get("/api/reload")
    assert "window.location.reload()" in resp.text


def test_reload_triggers_page_reload_on_new_ranges(tmp_path: Path):
    """When reloaded deck has new range signals, force full page reload."""
    from stardeck.server import create_app

    md_file = mk_deck(tmp_path, "# S1\n<click>A</click>")
    app, _rt, state = create_app(md_file)
    client = TestClient(app)

    md_file.write_text('# S1\n<click>A</click>\n<click at="2-4">B</click>')
    resp = client.get("/api/reload")
    assert "window.location.reload()" in resp.text


# --- Assets dir registration ---


def test_server_with_assets_dir(tmp_path: Path):
    from stardeck.server import create_app

    md_file = mk_deck(tmp_path, "# S1")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "img.png").write_bytes(b"\x89PNG")
    app, _rt, _state = create_app(md_file)
    # Asset should be served
    resp = TestClient(app).get("/assets/img.png")
    assert resp.status_code == 200
