"""Tests for watch mode file detection."""

import asyncio

import pytest

from stardeck.watch import FileWatcher, create_file_watcher


@pytest.mark.asyncio
async def test_file_watcher_detects_change(tmp_path):
    """Watcher should detect file modification."""
    md_file = tmp_path / "slides.md"
    md_file.write_text("# Slide 1")

    changes_detected = []
    watcher = create_file_watcher(md_file, lambda: changes_detected.append(True))

    # Start watcher in background
    task = asyncio.create_task(watcher.start())
    await asyncio.sleep(0.1)

    # Modify file
    md_file.write_text("# Slide 1 modified")
    await asyncio.sleep(0.5)

    # Graceful stop using stop_event
    watcher.stop()
    await asyncio.sleep(0.1)  # Give time for stop to propagate
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    assert len(changes_detected) > 0


def test_file_watcher_has_stop_method(tmp_path):
    """Watcher should have a stop method."""
    md_file = tmp_path / "slides.md"
    md_file.write_text("# Slide 1")

    watcher = create_file_watcher(md_file, lambda: None)
    assert hasattr(watcher, "stop")
    assert callable(watcher.stop)


def test_file_watcher_factory():
    """Factory function should return FileWatcher instance."""
    from pathlib import Path

    watcher = create_file_watcher(Path("test.md"), lambda: None)
    assert isinstance(watcher, FileWatcher)
