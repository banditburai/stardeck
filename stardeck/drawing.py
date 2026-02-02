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
