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
