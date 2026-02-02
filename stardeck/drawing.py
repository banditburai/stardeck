"""Drawing data models for StarDeck annotations."""

from dataclasses import dataclass, field
from typing import Union


@dataclass
class Point:
    """A point in the drawing coordinate system (0-100 percentage based)."""

    x: float
    y: float
    pressure: float = 1.0


@dataclass
class PenElement:
    """Freehand drawing path."""

    id: str
    type: str
    stroke_color: str
    stroke_width: int
    points: list[Point]
    slide_index: int


@dataclass
class LineElement:
    """Line or arrow element."""

    id: str
    type: str
    stroke_color: str
    stroke_width: int
    points: list[Point]
    start_arrow: bool
    end_arrow: bool
    slide_index: int


@dataclass
class ShapeElement:
    """Rectangle, ellipse, or diamond shape."""

    id: str
    type: str
    x: float
    y: float
    width: float
    height: float
    stroke_color: str
    stroke_width: int
    fill_color: str | None
    slide_index: int


@dataclass
class TextElement:
    """Text box element."""

    id: str
    type: str
    x: float
    y: float
    text: str
    font_size: int
    font_family: str
    stroke_color: str
    slide_index: int


# Union type for all drawing elements
DrawingElement = Union[PenElement, LineElement, ShapeElement, TextElement]


@dataclass
class DrawingState:
    """Server-side state for presenter drawings."""

    elements: dict[int, list[DrawingElement]] = field(default_factory=dict)
    undo_stack: list[dict] = field(default_factory=list)
    redo_stack: list[dict] = field(default_factory=list)

    def add_element(self, element: DrawingElement) -> None:
        """Add a drawing element to the state."""
        slide_index = element.slide_index
        if slide_index not in self.elements:
            self.elements[slide_index] = []
        self.elements[slide_index].append(element)
        # Track for undo
        self.undo_stack.append({"type": "add", "element": element})
        # Clear redo stack on new action
        self.redo_stack.clear()


def _points_to_path(points: list[Point]) -> str:
    """Convert a list of points to an SVG path string with smooth curves.

    Uses quadratic Bezier curves for smoothing between points.
    """
    if len(points) < 2:
        if len(points) == 1:
            return f"M {points[0].x} {points[0].y}"
        return ""

    d = f"M {points[0].x} {points[0].y}"

    for i in range(1, len(points) - 1):
        # Calculate midpoint for smooth curve
        xc = (points[i].x + points[i + 1].x) / 2
        yc = (points[i].y + points[i + 1].y) / 2
        d += f" Q {points[i].x} {points[i].y} {xc} {yc}"

    # Final line to last point
    last = points[-1]
    d += f" L {last.x} {last.y}"

    return d


def element_to_svg(element: DrawingElement) -> str:
    """Convert a drawing element to an SVG element string.

    Args:
        element: A drawing element (PenElement, LineElement, ShapeElement, TextElement)

    Returns:
        SVG element string
    """
    if isinstance(element, PenElement):
        path_d = _points_to_path(element.points)
        return (
            f'<path id="{element.id}" '
            f'd="{path_d}" '
            f'stroke="{element.stroke_color}" '
            f'stroke-width="{element.stroke_width}" '
            f'fill="none" '
            f'stroke-linecap="round" '
            f'stroke-linejoin="round" />'
        )

    if isinstance(element, LineElement):
        if len(element.points) < 2:
            return ""
        start, end = element.points[0], element.points[1]
        return (
            f'<line id="{element.id}" '
            f'x1="{start.x}" y1="{start.y}" '
            f'x2="{end.x}" y2="{end.y}" '
            f'stroke="{element.stroke_color}" '
            f'stroke-width="{element.stroke_width}" />'
        )

    if isinstance(element, ShapeElement):
        fill = element.fill_color or "none"
        if element.type == "rect":
            return (
                f'<rect id="{element.id}" '
                f'x="{element.x}" y="{element.y}" '
                f'width="{element.width}" height="{element.height}" '
                f'stroke="{element.stroke_color}" '
                f'stroke-width="{element.stroke_width}" '
                f'fill="{fill}" />'
            )
        if element.type == "ellipse":
            cx = element.x + element.width / 2
            cy = element.y + element.height / 2
            rx = element.width / 2
            ry = element.height / 2
            return (
                f'<ellipse id="{element.id}" '
                f'cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" '
                f'stroke="{element.stroke_color}" '
                f'stroke-width="{element.stroke_width}" '
                f'fill="{fill}" />'
            )

    if isinstance(element, TextElement):
        return (
            f'<text id="{element.id}" '
            f'x="{element.x}" y="{element.y}" '
            f'fill="{element.stroke_color}" '
            f'font-size="{element.font_size}" '
            f'font-family="{element.font_family}">'
            f'{element.text}</text>'
        )

    return ""
