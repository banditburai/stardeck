"""Tests for the StarDeck presenter mode."""

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


def test_presenter_route_exists(client: TestClient):
    """Test that /presenter route exists and returns 200."""
    response = client.get("/presenter")
    assert response.status_code == 200
    assert "presenter" in response.text.lower()


def test_presenter_has_current_slide(client: TestClient):
    """Test that presenter view has a current slide panel."""
    response = client.get("/presenter")
    html = response.text
    assert "current-slide" in html or "presenter-current" in html


def test_presenter_has_notes_panel(client: TestClient):
    """Test that presenter view has a notes panel."""
    response = client.get("/presenter")
    html = response.text
    assert "notes" in html.lower()


def test_presenter_has_next_slide_preview(client: TestClient):
    """Test that presenter view has a next slide preview."""
    response = client.get("/presenter")
    html = response.text
    assert "presenter-next" in html or "next-slide" in html


def test_presenter_shows_speaker_notes(tmp_path: Path):
    """Test that presenter view displays speaker notes from slide."""
    from stardeck.server import create_app

    md_file = tmp_path / "slides.md"
    md_file.write_text("# Slide 1\n\n<!-- notes\nThese are my speaker notes.\n-->")

    app, rt, deck_state = create_app(md_file)
    client = TestClient(app)

    response = client.get("/presenter")
    # Verify the actual note content appears in the response
    assert "These are my speaker notes" in response.text


def test_presenter_has_timer(client: TestClient):
    """Test that presenter view has an elapsed timer."""
    response = client.get("/presenter")
    html = response.text
    assert "timer" in html.lower() or "elapsed" in html.lower()


def test_presenter_navigation_updates_audience(client: TestClient):
    """Test that presenter navigation triggers SSE for all clients."""
    response = client.get("/presenter")
    html = response.text
    # Presenter should have navigation that updates server state
    assert "/api/slide/" in html


def test_presenter_has_keyboard_navigation(client: TestClient):
    """Test that presenter view has keyboard navigation handler."""
    response = client.get("/presenter")
    html = response.text
    assert "data-on-keydown" in html or "data-on:keydown" in html
