"""StarDeck CLI - Developer-first presentation tool."""

import os
import re
import select
import shutil
import subprocess
import threading
import time
from pathlib import Path

import click

from stardeck.server import create_app

# --- Tunnel ---

_URL_RE = re.compile(r"(https://[\w.-]+\.pinggy\.(?:link|online))")
_STARTUP_TIMEOUT = 15


def start_tunnel(port: int, token: str | None = None) -> tuple[subprocess.Popen, str]:
    if not shutil.which("ssh"):
        raise FileNotFoundError("SSH not found. Install OpenSSH to use --share.")

    host = "pro.pinggy.io" if token else "a.pinggy.io"
    target = f"{token}@{host}" if token else host
    cmd = [
        "ssh",
        "-p",
        "443",
        f"-R0:localhost:{port}",
        "-o",
        "StrictHostKeyChecking=accept-new",
        "-o",
        "ServerAliveInterval=30",
        target,
    ]

    env = os.environ.copy()
    if not token:
        # Suppress free-tier password prompt without a tty
        askpass = shutil.which("echo") or "/bin/echo"
        env["SSH_ASKPASS"] = askpass
        env["SSH_ASKPASS_REQUIRE"] = "force"

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        env=env,
    )
    assert proc.stdout

    url = _read_url(proc, _STARTUP_TIMEOUT)
    if url is None:
        try:
            output = os.read(proc.stdout.fileno(), 2000).decode("utf-8", errors="replace")
        except Exception:
            output = ""
        stop_tunnel(proc)
        detail = f"\n\nSSH output:\n{output[:500]}" if output else ""
        raise RuntimeError(f"Could not establish tunnel (timed out waiting for URL).{detail}")

    threading.Thread(target=_drain, args=(proc,), daemon=True).start()
    return proc, url


def _read_url(proc: subprocess.Popen, timeout: float) -> str | None:
    deadline = time.monotonic() + timeout
    fd = proc.stdout.fileno()
    buf = ""

    while (remaining := deadline - time.monotonic()) > 0:
        ready, _, _ = select.select([fd], [], [], min(remaining, 1.0))
        if ready:
            chunk = os.read(fd, 4096)
            if not chunk:
                break
            buf += chunk.decode("utf-8", errors="replace")
            if match := _URL_RE.search(buf):
                return match.group(1)
        if proc.poll() is not None:
            break

    return None


# Pipe buffer can block SSH if not drained
def _drain(proc: subprocess.Popen) -> None:
    try:
        while os.read(proc.stdout.fileno(), 4096):
            pass
    except (OSError, ValueError):
        pass


def stop_tunnel(proc: subprocess.Popen) -> None:
    try:
        proc.terminate()
    except ProcessLookupError:
        return
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=2)


# --- CLI commands ---


@click.group()
@click.version_option(package_name="stardeck")
def cli():
    """StarDeck - Developer-first presentation tool for Python."""


@cli.command()
@click.argument("slides", type=click.Path(exists=True, path_type=Path))
@click.option("--port", "-p", default=5001, help="Port to run the server on.")
@click.option("--theme", "-t", default=None, help="Theme (default: from frontmatter or 'default').")
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

        click.echo("Starting public tunnel...")
        try:
            tunnel_proc, tunnel_url = start_tunnel(port, token=share_token)
        except (FileNotFoundError, RuntimeError) as e:
            raise click.ClickException(str(e))
        atexit.register(stop_tunnel, tunnel_proc)

    app, _, state = create_app(slides, theme=theme, watch=watch)
    deck = state.deck
    presenter_token = state.presenter_token

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
@click.option("--theme", "-t", default=None, help="Theme (default: from frontmatter or 'default').")
def export(slides: Path, output: Path, theme: str):
    """Export a presentation as standalone HTML."""
    from stardeck.export import export_deck

    result = export_deck(slides, output, theme)
    click.echo(f"Exported to {result}/")
    click.echo(f"  Open {result / 'index.html'} in a browser to view.")


if __name__ == "__main__":
    cli()
