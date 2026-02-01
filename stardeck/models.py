"""Data models for StarDeck."""

from dataclasses import dataclass, field


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

    @property
    def layout(self) -> str:
        return self.frontmatter.get("layout", "default")

    @property
    def transition(self) -> str:
        return self.frontmatter.get("transition", "fade")

    @property
    def background(self) -> str | None:
        return self.frontmatter.get("background")
