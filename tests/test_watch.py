"""Tests for watch mode file detection."""

import asyncio

import pytest

from stardeck.server import FileWatcher


@pytest.mark.asyncio
async def test_file_watcher_detects_change(tmp_path):
    """Watcher should detect file modification."""
    md_file = tmp_path / "slides.md"
    md_file.write_text("# Slide 1")

    changes_detected = []
    watcher = FileWatcher(md_file, lambda: changes_detected.append(True))

    task = asyncio.create_task(watcher.start())
    await asyncio.sleep(0.1)

    md_file.write_text("# Slide 1 modified")
    await asyncio.sleep(0.5)

    watcher.stop()
    await asyncio.sleep(0.1)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

    assert len(changes_detected) > 0


def test_file_watcher_resolves_path(tmp_path):
    """Watcher should resolve relative paths for reliable comparison."""
    md_file = tmp_path / "slides.md"
    md_file.write_text("# Slide 1")

    watcher = FileWatcher(md_file, lambda: None)
    assert watcher.path.is_absolute()
    assert watcher.path == md_file.resolve()
