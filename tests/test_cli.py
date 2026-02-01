"""Tests for CLI interface."""

from click.testing import CliRunner

from stardeck.cli import cli


def test_cli_help():
    """CLI should show help with stardeck name."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "stardeck" in result.output.lower()


def test_cli_run_help():
    """Run command should have help."""
    runner = CliRunner()
    result = runner.invoke(cli, ["run", "--help"])
    assert result.exit_code == 0
    assert "slides" in result.output.lower() or "file" in result.output.lower()
