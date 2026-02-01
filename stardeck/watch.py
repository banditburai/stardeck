"""Watch mode file detection for StarDeck."""

from pathlib import Path
from typing import Callable

from watchfiles import awatch


class FileWatcher:
    """Watches a file for changes and triggers a callback."""

    def __init__(self, path: Path, on_change: Callable[[], None]):
        """Initialize the file watcher.

        Args:
            path: Path to the file to watch.
            on_change: Callback to invoke when file changes.
        """
        self.path = path
        self.on_change = on_change
        self._running = False

    async def start(self):
        """Start watching the file for changes."""
        self._running = True
        async for changes in awatch(self.path):
            if not self._running:
                break
            for change_type, changed_path in changes:
                if Path(changed_path) == self.path:
                    self.on_change()

    def stop(self):
        """Stop watching the file."""
        self._running = False


def create_file_watcher(path: Path, on_change: Callable[[], None]) -> FileWatcher:
    """Create a file watcher.

    Args:
        path: Path to the file to watch.
        on_change: Callback to invoke when file changes.

    Returns:
        A FileWatcher instance.
    """
    return FileWatcher(path, on_change)
