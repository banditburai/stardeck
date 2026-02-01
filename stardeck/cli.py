"""StarDeck CLI - Developer-first presentation tool."""

from pathlib import Path

import click

from stardeck.server import create_app


@click.group()
@click.version_option(package_name="stardeck")
def cli():
    """StarDeck - Developer-first presentation tool for Python."""
    pass


@cli.command()
@click.argument("slides", type=click.Path(exists=True, path_type=Path))
@click.option("--port", "-p", default=5001, help="Port to run the server on.")
@click.option("--debug", "-d", is_flag=True, help="Enable debug mode with live reload.")
def run(slides: Path, port: int, debug: bool):
    """Run a presentation from a markdown SLIDES file."""
    import uvicorn

    app, rt, deck_state = create_app(slides, debug=debug)
    deck = deck_state["deck"]
    click.echo(f"Starting StarDeck on http://localhost:{port}")
    click.echo(f"Slides: {deck.total}")
    # Use uvicorn directly for dynamic apps (created at runtime with slides path).
    # starhtml's serve() expects a module:variable path for uvicorn reload mode,
    # which doesn't work for apps created dynamically.
    uvicorn.run(app, host="localhost", port=port)


if __name__ == "__main__":
    cli()
