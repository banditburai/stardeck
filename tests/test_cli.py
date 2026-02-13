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


def test_export_command_help():
    """Export command help includes --output and --theme."""
    runner = CliRunner()
    result = runner.invoke(cli, ["export", "--help"])
    assert result.exit_code == 0
    assert "--output" in result.output
    assert "--theme" in result.output


def test_export_command_creates_output(tmp_path):
    """Export command creates index.html in the output directory."""
    md = tmp_path / "slides.md"
    md.write_text("# Hello\n---\n# World")
    runner = CliRunner()
    out_dir = tmp_path / "dist"
    result = runner.invoke(cli, ["export", str(md), "--output", str(out_dir)])
    assert result.exit_code == 0
    assert (out_dir / "index.html").exists()


def test_run_share_token_implies_share():
    """Run command help includes --share and --share-token."""
    runner = CliRunner()
    result = runner.invoke(cli, ["run", "--help"])
    assert "--share" in result.output
    assert "--share-token" in result.output
