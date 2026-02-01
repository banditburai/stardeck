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
    from starhtml import serve

    app, rt, deck = create_app(slides, debug=debug)
    click.echo(f"Starting StarDeck on http://127.0.0.1:{port}")
    click.echo(f"Slides: {deck.total}")
    serve(app, port=port, reload=debug)


if __name__ == "__main__":
    cli()
