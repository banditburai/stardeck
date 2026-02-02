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
