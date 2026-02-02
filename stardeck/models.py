"""Data models for StarDeck."""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class SlideInfo:
    """Represents a single slide with content and metadata."""

    content: str
    raw: str
    index: int
    start_line: int
    end_line: int
    frontmatter: dict = field(default_factory=dict)
    note: str = ""
    title: str = ""
    max_clicks: int = 0

    @property
    def layout(self) -> str:
        return self.frontmatter.get("layout", "default")

    @property
    def transition(self) -> str:
        return self.frontmatter.get("transition", "fade")

    @property
    def background(self) -> str | None:
        return self.frontmatter.get("background")


@dataclass(frozen=True)
class DeckConfig:
    """Configuration for the entire slide deck."""

    title: str = "Untitled"
    theme: str = "default"
    aspect_ratio: str = "16/9"
    transition: str = "fade"
    code_theme: str = "monokai"


@dataclass
class Deck:
    """A complete slide deck with slides, config, and metadata."""

    slides: list[SlideInfo]
    config: DeckConfig
    filepath: Path
    raw: str

    @property
    def total(self) -> int:
        return len(self.slides)
