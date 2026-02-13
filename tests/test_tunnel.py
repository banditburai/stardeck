"""Tests for Pinggy SSH tunnel."""

from unittest.mock import MagicMock, patch

import click
import pytest
from click.testing import CliRunner

from stardeck.cli import cli
from stardeck.tunnel import start_tunnel, stop_tunnel


def test_start_tunnel_no_ssh():
    with patch("stardeck.tunnel.shutil.which", return_value=None):
        with pytest.raises(click.ClickException, match="SSH not found"):
            start_tunnel(5001)


def test_url_extraction():
    mock_proc = MagicMock()
    mock_proc.stdout.fileno.return_value = 99
    mock_proc.poll.return_value = None

    with (
        patch("stardeck.tunnel.shutil.which", return_value="/usr/bin/ssh"),
        patch("stardeck.tunnel.subprocess.Popen", return_value=mock_proc),
        patch("stardeck.tunnel.select.select", return_value=([99], [], [])),
        patch("stardeck.tunnel.os.read", side_effect=[
            b"Warning: Permanently added 'a.pinggy.io' to known hosts.\n",
            b"http://rndzz-123.a.free.pinggy.link\n",
            b"https://rndzz-123.a.free.pinggy.link\n",
        ]),
        patch("stardeck.tunnel.threading.Thread") as mock_thread,
    ):
        proc, url = start_tunnel(5001)

    assert url == "https://rndzz-123.a.free.pinggy.link"
    assert proc is mock_proc
    mock_thread.return_value.start.assert_called_once()


def test_start_tunnel_timeout():
    mock_proc = MagicMock()
    mock_proc.stdout.fileno.return_value = 99
    mock_proc.stdout.readable.return_value = True
    mock_proc.stdout.read.return_value = "connection refused\n"
    mock_proc.poll.return_value = None

    with (
        patch("stardeck.tunnel.shutil.which", return_value="/usr/bin/ssh"),
        patch("stardeck.tunnel.subprocess.Popen", return_value=mock_proc),
        patch("stardeck.tunnel.select.select", return_value=([], [], [])),
        patch("stardeck.tunnel.STARTUP_TIMEOUT", 0),
    ):
        with pytest.raises(click.ClickException, match="Could not establish tunnel"):
            start_tunnel(5001)

    mock_proc.terminate.assert_called_once()


def test_start_tunnel_ssh_exits_early():
    mock_proc = MagicMock()
    mock_proc.stdout.fileno.return_value = 99
    mock_proc.stdout.readable.return_value = True
    mock_proc.stdout.read.return_value = "Permission denied\n"
    mock_proc.poll.side_effect = [None, 1]

    with (
        patch("stardeck.tunnel.shutil.which", return_value="/usr/bin/ssh"),
        patch("stardeck.tunnel.subprocess.Popen", return_value=mock_proc),
        patch("stardeck.tunnel.select.select", return_value=([99], [], [])),
        patch("stardeck.tunnel.os.read", return_value=b""),
    ):
        with pytest.raises(click.ClickException, match="Could not establish tunnel"):
            start_tunnel(5001)


def test_start_tunnel_uses_pro_host_with_token():
    mock_proc = MagicMock()
    mock_proc.stdout.fileno.return_value = 99
    mock_proc.poll.return_value = None

    with (
        patch("stardeck.tunnel.shutil.which", return_value="/usr/bin/ssh"),
        patch("stardeck.tunnel.subprocess.Popen", return_value=mock_proc) as mock_popen,
        patch("stardeck.tunnel.select.select", return_value=([99], [], [])),
        patch("stardeck.tunnel.os.read", side_effect=[
            b"https://myapp.a.pinggy.online\n",
        ]),
        patch("stardeck.tunnel.threading.Thread"),
    ):
        start_tunnel(5001, token="abc123")

    cmd = mock_popen.call_args[0][0]
    assert "abc123@pro.pinggy.io" in cmd


def test_stop_tunnel_already_dead():
    mock_proc = MagicMock()
    mock_proc.poll.return_value = 0

    stop_tunnel(mock_proc)

    mock_proc.terminate.assert_not_called()


def test_stop_tunnel_terminates():
    mock_proc = MagicMock()
    mock_proc.poll.return_value = None

    stop_tunnel(mock_proc)

    mock_proc.terminate.assert_called_once()
    mock_proc.wait.assert_called_once_with(timeout=5)


def test_cli_share_flag_exists():
    runner = CliRunner()
    result = runner.invoke(cli, ["run", "--help"])
    assert "--share" in result.output
    assert "--share-token" in result.output
