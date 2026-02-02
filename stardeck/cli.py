"""StarDeck CLI - Developer-first presentation tool."""

import asyncio
import threading
from pathlib import Path

import click

from stardeck.server import create_app
from stardeck.watch import create_file_watcher


@click.group()
@click.version_option(package_name="stardeck")
def cli():
    """StarDeck - Developer-first presentation tool for Python."""
    pass


@cli.command()
@click.argument("slides", type=click.Path(exists=True, path_type=Path))
@click.option("--port", "-p", default=5001, help="Port to run the server on.")
@click.option("--debug", "-d", is_flag=True, help="Enable debug mode with live reload.")
@click.option("--watch", "-w", is_flag=True, help="Watch for file changes and hot reload.")
def run(slides: Path, port: int, debug: bool, watch: bool):
    """Run a presentation from a markdown SLIDES file."""
    import time

    import uvicorn

    app, rt, deck_state = create_app(slides, debug=debug, watch=watch)
    deck = deck_state["deck"]
    presenter_token = deck_state["presenter_token"]

    click.echo(f"Starting StarDeck on http://localhost:{port}")
    click.echo(f"Slides: {deck.total}")
    click.echo("")
    click.echo(f"  Audience:  http://localhost:{port}")
    click.echo(f"  Presenter: http://localhost:{port}/presenter?token={presenter_token}")
    click.echo("")
    if watch:
        click.echo("Watch mode enabled - file changes will trigger hot reload")

    # Start file watcher in background thread when watch mode is enabled
    if watch:
        def on_file_change():
            deck_state["reload_timestamp"] = int(time.time() * 1000)

        watcher = create_file_watcher(slides, on_file_change)

        def watch_thread():
            asyncio.run(watcher.start())

        thread = threading.Thread(target=watch_thread, daemon=True)
        thread.start()

    # Use uvicorn directly for dynamic apps (created at runtime with slides path).
    # starhtml's serve() expects a module:variable path for uvicorn reload mode,
    # which doesn't work for apps created dynamically.
    uvicorn.run(app, host="localhost", port=port)


if __name__ == "__main__":
    cli()
