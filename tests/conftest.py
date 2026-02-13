"""Shared test fixtures and helpers."""

import json
import re
from pathlib import Path

import pytest
from starlette.testclient import TestClient


def parse_sse_signals(text: str) -> dict:
    """Extract merged signal dict from SSE `data: signals {...}` lines."""
    merged = {}
    for m in re.finditer(r"data:\s*signals\s+(\{.*?\})", text):
        merged.update(json.loads(m.group(1)))
    return merged


def mk_deck(tmp_path: Path, text: str) -> Path:
    """Write markdown to a temp file and return its path."""
    md = tmp_path / "slides.md"
    md.write_text(text)
    return md


@pytest.fixture
def deck_path(tmp_path: Path) -> Path:
    """3-slide deck with no clicks."""
    return mk_deck(tmp_path, "# Slide 1\n---\n# Slide 2\n---\n# Slide 3")


@pytest.fixture
def app_and_state(deck_path: Path):
    """Create app and return (app, deck_state)."""
    from stardeck.server import create_app

    app, _rt, deck_state = create_app(deck_path)
    return app, deck_state


@pytest.fixture
def client(app_and_state) -> TestClient:
    """TestClient wrapping the app."""
    app, _ = app_and_state
    return TestClient(app)


@pytest.fixture
def presenter_token(app_and_state) -> str:
    """Presenter authentication token."""
    _, deck_state = app_and_state
    return deck_state["presenter_token"]
