"""Watch mode file detection for StarDeck."""

import asyncio
from pathlib import Path
from typing import Callable

from watchfiles import awatch


class FileWatcher:
    """Watches a file for changes and triggers a callback."""

    def __init__(self, path: Path, on_change: Callable[[], None]):
        self.path = path.resolve()
        self.on_change = on_change
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        self._stop_event.clear()
        async for changes in awatch(self.path, stop_event=self._stop_event):
            for _, changed_path in changes:
                if Path(changed_path) == self.path:
                    self.on_change()

    def stop(self) -> None:
        self._stop_event.set()
