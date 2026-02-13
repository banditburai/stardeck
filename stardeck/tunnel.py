"""Pinggy SSH tunnel for sharing presentations publicly."""

import os
import re
import select
import shutil
import subprocess
import threading
import time

import click

URL_RE = re.compile(r"(https://[\w.-]+\.pinggy\.(?:link|online))")
STARTUP_TIMEOUT = 15


def start_tunnel(port: int, token: str | None = None) -> tuple[subprocess.Popen, str]:
    """Start a Pinggy SSH tunnel and return (process, public_url)."""
    if not shutil.which("ssh"):
        raise click.ClickException("SSH not found. Install OpenSSH to use --share.")

    host = "pro.pinggy.io" if token else "a.pinggy.io"
    target = f"{token}@{host}" if token else host
    cmd = [
        "ssh", "-p", "443",
        f"-R0:localhost:{port}",
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", "ServerAliveInterval=30",
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
        text=True,
        env=env,
    )

    url = _read_url(proc, STARTUP_TIMEOUT)
    if url is None:
        output = ""
        if proc.stdout and proc.stdout.readable():
            try:
                output = proc.stdout.read(2000)
            except Exception:
                pass
        stop_tunnel(proc)
        msg = "Could not establish tunnel (timed out waiting for URL)."
        if output:
            msg += f"\n\nSSH output:\n{output[:500]}"
        raise click.ClickException(msg)

    threading.Thread(target=_drain, args=(proc,), daemon=True).start()
    return proc, url


def _read_url(proc: subprocess.Popen, timeout: float) -> str | None:
    """Poll proc.stdout for a pinggy URL within timeout seconds."""
    deadline = time.monotonic() + timeout
    fd = proc.stdout.fileno()
    buf = ""

    while time.monotonic() < deadline:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        ready, _, _ = select.select([fd], [], [], min(remaining, 1.0))
        if ready:
            chunk = os.read(fd, 4096)
            if not chunk:
                break
            buf += chunk.decode("utf-8", errors="replace")
            match = URL_RE.search(buf)
            if match:
                return match.group(1)
        if proc.poll() is not None:
            break

    return None


def _drain(proc: subprocess.Popen) -> None:
    """Discard remaining stdout so the pipe buffer doesn't block SSH."""
    try:
        for _ in proc.stdout:
            pass
    except Exception:
        pass


def stop_tunnel(proc: subprocess.Popen) -> None:
    """Terminate the tunnel process cleanly."""
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=2)
