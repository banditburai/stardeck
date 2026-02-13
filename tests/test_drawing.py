"""Tests for stardeck drawing system (star-drawing web component integration)."""

from pathlib import Path

from starlette.testclient import TestClient


def test_audience_has_drawing_canvas(client):
    """Audience view should contain a readonly drawing-canvas component."""
    response = client.get("/")
    assert response.status_code == 200
    assert "audience-canvas" in response.text
    assert "drawing-canvas" in response.text


def test_drawing_canvas_is_readonly(client):
    """Audience canvas should have readonly attribute."""
    response = client.get("/")
    assert response.status_code == 200
    assert "readonly" in response.text


def test_drawing_store_apply_and_snapshot():
    """DrawingStore should apply changes and return snapshots."""
    from stardeck.models import DrawingStore

    store = DrawingStore()
    changes = [
        {"type": "create", "element": {"id": "el-1", "kind": "pen", "points": []}},
        {"type": "create", "element": {"id": "el-2", "kind": "rect", "x": 10}},
    ]
    store.apply_changes(0, changes)

    snapshot = store.get_snapshot(0)
    assert len(snapshot) == 3  # 2 creates + 1 reorder
    element_ids = [c["element"]["id"] for c in snapshot if c["type"] == "create"]
    assert "el-1" in element_ids
    assert "el-2" in element_ids


def test_drawing_store_delete():
    """DrawingStore should handle delete changes."""
    from stardeck.models import DrawingStore

    store = DrawingStore()
    store.apply_changes(
        0,
        [
            {"type": "create", "element": {"id": "el-1", "kind": "pen"}},
            {"type": "create", "element": {"id": "el-2", "kind": "rect"}},
        ],
    )
    store.apply_changes(0, [{"type": "delete", "elementId": "el-1"}])

    snapshot = store.get_snapshot(0)
    element_ids = [c["element"]["id"] for c in snapshot if c["type"] == "create"]
    assert element_ids == ["el-2"]


def test_drawing_store_update():
    """DrawingStore should handle update changes."""
    from stardeck.models import DrawingStore

    store = DrawingStore()
    store.apply_changes(
        0,
        [
            {"type": "create", "element": {"id": "el-1", "color": "red"}},
        ],
    )
    store.apply_changes(
        0,
        [
            {"type": "update", "element": {"id": "el-1", "color": "blue"}},
        ],
    )

    snapshot = store.get_snapshot(0)
    elements = [c["element"] for c in snapshot if c["type"] == "create"]
    assert elements[0]["color"] == "blue"


def test_drawing_store_multiple_slides():
    """DrawingStore should keep elements separated by slide."""
    from stardeck.models import DrawingStore

    store = DrawingStore()
    store.apply_changes(0, [{"type": "create", "element": {"id": "el-1"}}])
    store.apply_changes(1, [{"type": "create", "element": {"id": "el-2"}}])

    snap0 = store.get_snapshot(0)
    snap1 = store.get_snapshot(1)
    assert any(c["element"]["id"] == "el-1" for c in snap0 if c["type"] == "create")
    assert any(c["element"]["id"] == "el-2" for c in snap1 if c["type"] == "create")


def test_drawing_store_reorder():
    """DrawingStore should reorder elements and filter out deleted IDs."""
    from stardeck.models import DrawingStore

    store = DrawingStore()
    store.apply_changes(
        0,
        [
            {"type": "create", "element": {"id": "a"}},
            {"type": "create", "element": {"id": "b"}},
            {"type": "create", "element": {"id": "c"}},
        ],
    )
    store.apply_changes(0, [{"type": "reorder", "order": ["c", "a", "b"]}])

    snapshot = store.get_snapshot(0)
    reorder = [c for c in snapshot if c["type"] == "reorder"][0]
    assert reorder["order"] == ["c", "a", "b"]

    # Unknown IDs in reorder are filtered out
    store.apply_changes(0, [{"type": "reorder", "order": ["b", "unknown", "a", "c"]}])
    snapshot = store.get_snapshot(0)
    reorder = [c for c in snapshot if c["type"] == "reorder"][0]
    assert reorder["order"] == ["b", "a", "c"]


def test_drawing_store_empty_snapshot():
    """DrawingStore should return empty list for slides with no drawings."""
    from stardeck.models import DrawingStore

    store = DrawingStore()
    assert store.get_snapshot(0) == []
    assert store.get_snapshot(999) == []


def test_presentation_state_has_drawing_store(tmp_path: Path):
    """PresentationState should include DrawingStore."""
    from stardeck.models import DrawingStore
    from stardeck.server import create_app

    md_file = tmp_path / "slides.md"
    md_file.write_text("# Slide 1")

    _app, _rt, deck_state = create_app(md_file)
    pres = deck_state["presentation"]

    assert hasattr(pres, "drawing")
    assert isinstance(pres.drawing, DrawingStore)


def test_presenter_changes_endpoint(client: TestClient, presenter_token: str):
    """Presenter should be able to send drawing changes via POST."""
    response = client.post(
        f"/api/presenter/changes?token={presenter_token}",
        json={
            "changes": [
                {"type": "create", "element": {"id": "el-1", "kind": "pen"}},
            ],
            "slide_index": 0,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["applied"] == 1


def test_presenter_changes_requires_token(client: TestClient):
    """Changes endpoint should reject requests without valid token."""
    response = client.post(
        "/api/presenter/changes?token=bad-token",
        json={"changes": [{"type": "create", "element": {"id": "x"}}]},
    )
    assert response.status_code == 401


def test_presenter_changes_empty(client: TestClient, presenter_token: str):
    """Empty changes list should return ok with 0 applied."""
    response = client.post(
        f"/api/presenter/changes?token={presenter_token}",
        json={"changes": []},
    )
    assert response.status_code == 200
    assert response.json()["applied"] == 0


def test_presenter_has_drawing_canvas(client: TestClient, presenter_token: str):
    """Presenter view should contain a drawing-canvas component."""
    response = client.get(f"/presenter?token={presenter_token}")
    assert response.status_code == 200
    assert "drawing-canvas" in response.text


def test_presenter_has_drawing_toolbar(client: TestClient, presenter_token: str):
    """Presenter view should contain the star-drawing toolbar."""
    response = client.get(f"/presenter?token={presenter_token}")
    assert response.status_code == 200
    assert "toolbar-island" in response.text or "toolbar-bar" in response.text


def test_presenter_wires_element_change(client: TestClient, presenter_token: str):
    """Presenter should wire element-change events to the changes endpoint."""
    response = client.get(f"/presenter?token={presenter_token}")
    html = response.text
    assert "/api/presenter/changes" in html
