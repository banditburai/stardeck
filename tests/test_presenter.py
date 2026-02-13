"""Tests for the StarDeck presenter mode."""

from pathlib import Path

from starlette.testclient import TestClient

from .conftest import mk_deck


def test_presenter_route_exists(client: TestClient, presenter_token: str):
    response = client.get(f"/presenter?token={presenter_token}")
    assert response.status_code == 200
    assert "presenter" in response.text.lower()


def test_presenter_requires_token(client: TestClient):
    response = client.get("/presenter")
    assert response.status_code == 200
    assert "Access Denied" in response.text


def test_presenter_has_current_slide(client: TestClient, presenter_token: str):
    html = client.get(f"/presenter?token={presenter_token}").text
    assert "current-slide" in html or "presenter-current" in html


def test_presenter_has_notes_panel(client: TestClient, presenter_token: str):
    html = client.get(f"/presenter?token={presenter_token}").text
    assert 'id="presenter-notes"' in html


def test_presenter_has_next_slide_preview(client: TestClient, presenter_token: str):
    html = client.get(f"/presenter?token={presenter_token}").text
    assert "presenter-next" in html or "next-slide" in html


def test_presenter_shows_speaker_notes(tmp_path: Path):
    from stardeck.server import create_app

    md_file = mk_deck(tmp_path, "# Slide 1\n\n<!-- notes\nThese are my speaker notes.\n-->")
    app, _rt, deck_state = create_app(md_file)
    token = deck_state["presenter_token"]
    html = TestClient(app).get(f"/presenter?token={token}").text
    assert "These are my speaker notes" in html


def test_presenter_has_timer(client: TestClient, presenter_token: str):
    html = client.get(f"/presenter?token={presenter_token}").text
    assert "presenter-timer" in html


def test_presenter_navigation_updates_audience(client: TestClient, presenter_token: str):
    html = client.get(f"/presenter?token={presenter_token}").text
    assert "/api/presenter/" in html


def test_presenter_has_keyboard_navigation(client: TestClient, presenter_token: str):
    html = client.get(f"/presenter?token={presenter_token}").text
    assert "data-on-keydown" in html or "data-on:keydown" in html
