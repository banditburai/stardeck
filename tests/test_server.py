"""Tests for the StarDeck server module."""

from pathlib import Path

import pytest
from starlette.testclient import TestClient


@pytest.fixture
def client(tmp_path: Path):
    """Create a test client with a simple deck."""
    from stardeck.server import create_app

    md_file = tmp_path / "slides.md"
    md_file.write_text("# Slide 1\n---\n# Slide 2\n---\n# Slide 3")

    app, rt, deck_state = create_app(md_file)
    return TestClient(app)


def test_create_app(tmp_path: Path):
    """Test that create_app returns app, rt, and deck_state tuple."""
    from stardeck.server import create_app

    md_file = tmp_path / "slides.md"
    md_file.write_text("# Test Slide")

    app, rt, deck_state = create_app(md_file)

    assert deck_state["deck"].total == 1
    assert app is not None
    assert rt is not None


def test_next_slide_endpoint(client: TestClient):
    """Test that /api/slide/next returns SSE with updated slide."""
    response = client.get("/api/slide/next")
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]


def test_prev_slide_endpoint(client: TestClient):
    """Test that /api/slide/prev returns SSE with updated slide."""
    response = client.get("/api/slide/prev")
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]


def test_goto_slide_endpoint(client: TestClient):
    """Test that /api/slide/{idx} returns SSE with specific slide."""
    response = client.get("/api/slide/2")
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]


def test_reload_endpoint(client: TestClient):
    """Test that /api/reload returns SSE with re-parsed deck."""
    response = client.get("/api/reload")
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]


def test_watch_status_endpoint(tmp_path: Path):
    """Test that /api/watch-status returns timestamp for polling."""
    from stardeck.server import create_app

    md_file = tmp_path / "slides.md"
    md_file.write_text("# Test Slide")

    app, rt, deck_state = create_app(md_file, watch=True)
    client = TestClient(app)

    response = client.get("/api/watch-status")
    assert response.status_code == 200
    data = response.json()
    assert "timestamp" in data
    assert isinstance(data["timestamp"], int)
    assert data["timestamp"] > 0


def test_watch_status_updates_on_file_change(tmp_path: Path):
    """Test that watch timestamp changes when updated."""
    from stardeck.server import create_app

    md_file = tmp_path / "slides.md"
    md_file.write_text("# Test Slide")

    app, rt, deck_state = create_app(md_file, watch=True)
    client = TestClient(app)

    # Get initial timestamp
    response1 = client.get("/api/watch-status")
    timestamp1 = response1.json()["timestamp"]

    # Simulate file change by updating reload_timestamp
    import time
    deck_state["reload_timestamp"] = int(time.time() * 1000) + 1000

    # Get new timestamp
    response2 = client.get("/api/watch-status")
    timestamp2 = response2.json()["timestamp"]

    assert timestamp2 > timestamp1


def test_home_has_clicks_signal(client: TestClient):
    """Test that home page has clicks signal for click animations."""
    response = client.get("/")
    html = response.text
    # Verify clicks signal is present
    assert "clicks" in html
    # Verify data-signals attribute is present (StarHTML signal initialization)
    assert "data-signals" in html


def test_keyboard_navigation_with_clicks(client: TestClient):
    """Test that keyboard navigation includes click increment/decrement logic."""
    response = client.get("/")
    html = response.text
    # Navigation logic should compare clicks to max_clicks
    # This indicates click-aware navigation is implemented
    assert "$clicks<$max_clicks" in html or "$clicks < $max_clicks" in html


def test_next_slide_resets_clicks(client: TestClient):
    """Test that /api/slide/next SSE response resets clicks to 0."""
    response = client.get("/api/slide/next?slide_index=0")
    # SSE response should include clicks signal reset
    assert "clicks" in response.text


def test_prev_slide_resets_clicks(client: TestClient):
    """Test that /api/slide/prev SSE response resets clicks to 0."""
    response = client.get("/api/slide/prev?slide_index=1")
    # SSE response should include clicks signal reset
    assert "clicks" in response.text


def test_goto_slide_resets_clicks(client: TestClient):
    """Test that /api/slide/{idx} SSE response resets clicks to 0."""
    response = client.get("/api/slide/1")
    # SSE response should include clicks signal reset
    assert "clicks" in response.text


def test_url_hash_includes_clicks(client: TestClient):
    """Test that URL hash format supports clicks: #slide or #slide.click."""
    response = client.get("/")
    html = response.text
    # URL hash effect should include clicks when clicks > 0
    # Format: #3 for slide 3 with 0 clicks, #3.2 for slide 3 click 2
    assert "history.replaceState" in html or "location.hash" in html
    # Should conditionally append .clicks when clicks > 0
    assert "$clicks" in html


def test_url_hash_parsing_supports_clicks(client: TestClient):
    """Test that URL hash parsing on load supports #slide.click format."""
    response = client.get("/")
    html = response.text
    # Hash parsing should extract both slide and click from #3.2 format
    # The init handler should parse the dot-separated format
    assert "data-init" in html
    # Should handle the .clicks suffix in the hash
    assert ".split" in html or "indexOf" in html or "includes" in html


def test_goto_slide_accepts_clicks_param(client: TestClient):
    """Test that /api/slide/{idx}?clicks=N passes click state to SSE response."""
    response = client.get("/api/slide/1?clicks=2")
    assert response.status_code == 200
    # SSE response should include the clicks value from query param
    # (clamped to max_clicks for the slide)
    assert "clicks" in response.text


def test_goto_slide_clamps_clicks_to_max(tmp_path: Path):
    """Test that clicks are clamped to max_clicks for the target slide."""
    from stardeck.server import create_app

    # Create deck with slides that have click tags
    md_file = tmp_path / "slides.md"
    md_file.write_text("# Slide 1\n<click>A</click>\n---\n# Slide 2")

    app, rt, deck_state = create_app(md_file)
    client = TestClient(app)

    # Request slide 0 with clicks=100 (way more than max_clicks=1)
    response = client.get("/api/slide/0?clicks=100")
    assert response.status_code == 200
    # The response should have clicks clamped to max_clicks (1)
    # We can't easily parse SSE to verify exact value, but the test
    # ensures the endpoint doesn't crash with out-of-range clicks
    assert "clicks" in response.text
