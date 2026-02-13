"""StarDeck CLI - Developer-first presentation tool."""

from pathlib import Path

import click

from stardeck.server import create_app


@click.group()
@click.version_option(package_name="stardeck")
def cli():
    """StarDeck - Developer-first presentation tool for Python."""


@cli.command()
@click.argument("slides", type=click.Path(exists=True, path_type=Path))
@click.option("--port", "-p", default=5001, help="Port to run the server on.")
@click.option("--theme", "-t", default="default", help="Theme to use.")
@click.option("--watch", "-w", is_flag=True, help="Watch for file changes and hot reload.")
@click.option("--share", is_flag=True, help="Create a public tunnel to share the presentation.")
@click.option("--share-token", help="Pinggy token for persistent/custom tunnel URLs.")
def run(slides: Path, port: int, theme: str, watch: bool, share: bool, share_token: str):
    """Run a presentation from a markdown SLIDES file."""
    import uvicorn

    if share_token:
        share = True

    tunnel_url = None
    if share:
        import atexit

        from stardeck.tunnel import start_tunnel, stop_tunnel

        click.echo("Starting public tunnel...")
        try:
            tunnel_proc, tunnel_url = start_tunnel(port, token=share_token)
        except (FileNotFoundError, RuntimeError) as e:
            raise click.ClickException(str(e))
        atexit.register(stop_tunnel, tunnel_proc)

    app, _, deck_state = create_app(slides, theme=theme, watch=watch)
    deck = deck_state["deck"]
    presenter_token = deck_state["presenter_token"]

    click.echo(f"StarDeck - {deck.total} slides")
    click.echo("")
    click.echo(f"  Audience:  http://localhost:{port}")
    click.echo(f"  Presenter: http://localhost:{port}/presenter?token={presenter_token}")
    if tunnel_url:
        click.echo("")
        click.echo(f"  Public:    {tunnel_url}")
        if share_token:
            click.echo("  (share this URL with your audience)")
        else:
            click.echo("  (viewers see a one-time Pinggy trust page before entering)")
            click.echo("  Tip: use --share-token with Pinggy Pro to skip it")
    click.echo("")
    if watch:
        click.echo("Watch mode enabled - file changes will trigger hot reload")

    # starhtml's serve() needs a module:variable import path for uvicorn reload,
    # so we call uvicorn directly since the app is created dynamically.
    uvicorn.run(app, host="localhost", port=port)


@cli.command()
@click.argument("slides", type=click.Path(exists=True, path_type=Path))
@click.option("--output", "-o", default="dist", type=click.Path(path_type=Path), help="Output directory.")
@click.option("--theme", "-t", default="default", help="Theme to use.")
def export(slides: Path, output: Path, theme: str):
    """Export a presentation as standalone HTML."""
    from stardeck.export import export_deck

    result = export_deck(slides, output, theme)
    click.echo(f"Exported to {result}/")
    click.echo(f"  Open {result / 'index.html'} in a browser to view.")


if __name__ == "__main__":
    cli()
