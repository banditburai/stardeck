"""Tests for stardeck drawing data models."""

import pytest
from pathlib import Path
from starlette.testclient import TestClient


@pytest.fixture
def app_with_state(tmp_path: Path):
    """Create an app with deck state."""
    from stardeck.server import create_app

    md_file = tmp_path / "slides.md"
    md_file.write_text("# Slide 1\n---\n# Slide 2")

    app, rt, deck_state = create_app(md_file)
    return app, deck_state


@pytest.fixture
def client(app_with_state):
    """Create a test client."""
    app, _ = app_with_state
    return TestClient(app)


@pytest.fixture
def presenter_token(app_with_state):
    """Get the presenter token for authentication."""
    _, deck_state = app_with_state
    return deck_state["presenter_token"]


def test_drawing_layer_in_slide_viewport(client):
    """Drawing layer SVG should be present in the slide viewport."""
    response = client.get("/")
    assert response.status_code == 200
    assert "drawing-layer" in response.text
    assert "<svg" in response.text


def test_drawing_element_creation():
    """Point and PenElement should be creatable with required fields."""
    from stardeck.drawing import PenElement, Point

    point = Point(x=10.0, y=20.0, pressure=0.5)
    assert point.x == 10.0
    assert point.y == 20.0
    assert point.pressure == 0.5

    element = PenElement(
        id="el-1",
        type="pen",
        stroke_color="#ff0000",
        stroke_width=2,
        points=[point],
        slide_index=0,
    )
    assert element.type == "pen"
    assert len(element.points) == 1
    assert element.id == "el-1"
    assert element.stroke_color == "#ff0000"
    assert element.stroke_width == 2
    assert element.slide_index == 0


def test_point_pressure_defaults():
    """Point pressure should default to 1.0."""
    from stardeck.drawing import Point

    point = Point(x=50.0, y=50.0)
    assert point.pressure == 1.0


def test_line_element_creation():
    """LineElement should support start and end arrows."""
    from stardeck.drawing import LineElement, Point

    element = LineElement(
        id="line-1",
        type="line",
        stroke_color="#0000ff",
        stroke_width=2,
        points=[Point(10, 10), Point(90, 90)],
        start_arrow=False,
        end_arrow=True,
        slide_index=0,
    )
    assert element.type == "line"
    assert len(element.points) == 2
    assert element.start_arrow is False
    assert element.end_arrow is True


def test_shape_element_creation():
    """ShapeElement should store x, y, width, height."""
    from stardeck.drawing import ShapeElement

    element = ShapeElement(
        id="rect-1",
        type="rect",
        x=10.0,
        y=20.0,
        width=50.0,
        height=30.0,
        stroke_color="#00ff00",
        stroke_width=2,
        fill_color=None,
        slide_index=0,
    )
    assert element.type == "rect"
    assert element.x == 10.0
    assert element.y == 20.0
    assert element.width == 50.0
    assert element.height == 30.0
    assert element.fill_color is None


def test_text_element_creation():
    """TextElement should store text content and styling."""
    from stardeck.drawing import TextElement

    element = TextElement(
        id="text-1",
        type="text",
        x=50.0,
        y=50.0,
        text="Hello World",
        font_size=16,
        font_family="sans-serif",
        stroke_color="#000000",
        slide_index=0,
    )
    assert element.text == "Hello World"
    assert element.font_size == 16
    assert element.font_family == "sans-serif"


def test_drawing_state_add_element():
    """DrawingState should track elements by slide index."""
    from stardeck.drawing import DrawingState, PenElement, Point

    state = DrawingState()
    element = PenElement(
        id="el-1",
        type="pen",
        stroke_color="#f00",
        stroke_width=2,
        points=[Point(0, 0)],
        slide_index=0,
    )
    state.add_element(element)

    assert len(state.elements[0]) == 1
    assert state.elements[0][0].id == "el-1"


def test_drawing_state_multiple_slides():
    """DrawingState should keep elements separated by slide."""
    from stardeck.drawing import DrawingState, PenElement, Point

    state = DrawingState()
    el1 = PenElement(
        id="el-1", type="pen", stroke_color="#f00",
        stroke_width=2, points=[Point(0, 0)], slide_index=0
    )
    el2 = PenElement(
        id="el-2", type="pen", stroke_color="#0f0",
        stroke_width=2, points=[Point(10, 10)], slide_index=1
    )
    state.add_element(el1)
    state.add_element(el2)

    assert len(state.elements[0]) == 1
    assert len(state.elements[1]) == 1
    assert state.elements[0][0].id == "el-1"
    assert state.elements[1][0].id == "el-2"


def test_pen_element_to_svg_path():
    """PenElement should convert to SVG path string."""
    from stardeck.drawing import PenElement, Point, element_to_svg

    element = PenElement(
        id="pen-1",
        type="pen",
        stroke_color="#ff0000",
        stroke_width=2,
        points=[Point(10, 20), Point(30, 40), Point(50, 30)],
        slide_index=0,
    )
    svg = element_to_svg(element)
    assert "path" in svg
    assert 'stroke="#ff0000"' in svg
    assert "M 10" in svg  # Move to start point


def test_presentation_state_has_drawing(tmp_path: Path):
    """PresentationState should include DrawingState for annotations."""
    from stardeck.server import create_app
    from stardeck.drawing import DrawingState

    md_file = tmp_path / "slides.md"
    md_file.write_text("# Slide 1")

    app, rt, deck_state = create_app(md_file)
    pres = deck_state["presentation"]

    assert hasattr(pres, "drawing")
    assert isinstance(pres.drawing, DrawingState)


def test_presenter_draw_endpoint(client: TestClient, presenter_token: str):
    """Presenter should be able to add drawing elements via POST."""
    element_data = {
        "id": "el-1",
        "type": "pen",
        "stroke_color": "#ff0000",
        "stroke_width": 2,
        "points": [{"x": 10, "y": 20}],
        "slide_index": 0,
    }
    response = client.post(
        f"/api/presenter/draw?token={presenter_token}",
        json=element_data
    )
    assert response.status_code == 200


def test_drawing_element_to_dict():
    """Drawing elements should be serializable to dict for SSE broadcast."""
    from stardeck.drawing import PenElement, Point, element_to_dict

    element = PenElement(
        id="pen-1",
        type="pen",
        stroke_color="#ff0000",
        stroke_width=2,
        points=[Point(10, 20, 0.5), Point(30, 40)],
        slide_index=0,
    )
    d = element_to_dict(element)

    assert d["id"] == "pen-1"
    assert d["type"] == "pen"
    assert d["stroke_color"] == "#ff0000"
    assert d["slide_index"] == 0
    assert len(d["points"]) == 2
    assert d["points"][0]["x"] == 10
    assert d["points"][0]["pressure"] == 0.5
    assert d["points"][1]["pressure"] == 1.0  # default
