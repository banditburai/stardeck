"""Tests for watch mode file detection."""

import asyncio
from pathlib import Path

import pytest


def test_file_watcher_detects_change(tmp_path):
    """Watcher should detect file modification."""
    from stardeck.watch import create_file_watcher

    md_file = tmp_path / "slides.md"
    md_file.write_text("# Slide 1")

    changes_detected = []

    async def run_test():
        watcher = create_file_watcher(md_file, lambda: changes_detected.append(True))
        # Start watcher in background
        task = asyncio.create_task(watcher.start())
        await asyncio.sleep(0.1)

        # Modify file
        md_file.write_text("# Slide 1 modified")
        await asyncio.sleep(0.5)

        watcher.stop()
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    asyncio.run(run_test())
    assert len(changes_detected) > 0


def test_file_watcher_has_stop_method(tmp_path):
    """Watcher should have a stop method."""
    from stardeck.watch import create_file_watcher

    md_file = tmp_path / "slides.md"
    md_file.write_text("# Slide 1")

    watcher = create_file_watcher(md_file, lambda: None)
    assert hasattr(watcher, "stop")
    assert callable(watcher.stop)
