"""Opaque JSON drawing store for star-drawing web component relay."""

from dataclasses import dataclass, field


@dataclass
class DrawingStore:
    """Per-slide opaque element storage. Server stores JSON dicts as-is."""

    slides: dict[int, dict[str, dict]] = field(default_factory=dict)
    element_order: dict[int, list[str]] = field(default_factory=dict)

    def apply_changes(self, slide_index: int, changes: list[dict]) -> None:
        if slide_index not in self.slides:
            self.slides[slide_index] = {}
            self.element_order[slide_index] = []
        elements = self.slides[slide_index]
        order = self.element_order[slide_index]
        for change in changes:
            t = change.get("type")
            if t in ("create", "update"):
                el = change["element"]
                eid = el["id"]
                elements[eid] = el
                if eid not in order:
                    order.append(eid)
            elif t == "delete":
                eid = change["elementId"]
                elements.pop(eid, None)
                if eid in order:
                    order.remove(eid)
            elif t == "reorder":
                self.element_order[slide_index] = [
                    eid for eid in change["order"] if eid in elements
                ]

    def get_snapshot(self, slide_index: int) -> list[dict]:
        if slide_index not in self.slides:
            return []
        elements = self.slides[slide_index]
        order = self.element_order.get(slide_index, [])
        if not elements:
            return []
        snapshot = [{"type": "create", "element": el} for el in elements.values()]
        if order:
            snapshot.append({"type": "reorder", "order": order})
        return snapshot
