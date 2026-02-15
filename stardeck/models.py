"""Data models for StarDeck."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SlideInfo:
    content: str
    index: int
    frontmatter: dict = field(default_factory=dict)
    note: str = ""
    title: str = ""
    max_clicks: int = 0
    range_clicks: frozenset[tuple[int, int]] = field(default_factory=frozenset)

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
    title: str = "Untitled"
    transition: str = "fade"
    click_animation: str = "fade"
    click_duration: int | None = None
    click_delay: int | None = None
    click_ease: str | None = None
    click_spring: str | None = None


@dataclass
class Deck:
    slides: list[SlideInfo]
    config: DeckConfig

    @property
    def total(self) -> int:
        return len(self.slides)


@dataclass
class DrawingStore:
    """Opaque store — server holds drawing JSON as-is without interpretation."""

    _elements: dict[int, dict[str, dict]] = field(default_factory=dict)

    def apply_changes(self, slide_index: int, changes: list[dict]) -> None:
        elements = self._elements.setdefault(slide_index, {})
        for change in changes:
            t = change.get("type")
            if t in ("create", "update"):
                el = change["element"]
                elements[el["id"]] = el
            elif t == "delete":
                elements.pop(change["elementId"], None)
            elif t == "reorder":
                ordered = {eid: elements[eid] for eid in change["order"] if eid in elements}
                for eid, el in elements.items():
                    if eid not in ordered:
                        ordered[eid] = el
                self._elements[slide_index] = ordered

    def get_snapshot(self, slide_index: int) -> list[dict]:
        if not (elements := self._elements.get(slide_index)):
            return []
        snapshot = [{"type": "create", "element": el} for el in elements.values()]
        snapshot.append({"type": "reorder", "order": list(elements.keys())})
        return snapshot
