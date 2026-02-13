"""StarDeck theme system — CSS themes live in your codebase and can be customized."""

from importlib import import_module, resources
from pathlib import Path

_THEMES_DIR = Path(__file__).parent


def get_theme_css(theme_name: str = "default") -> str:
    """Load CSS for a theme by name. Raises FileNotFoundError if missing."""
    try:
        return resources.files(f"stardeck.themes.{theme_name}").joinpath("styles.css").read_text()
    except (ModuleNotFoundError, FileNotFoundError, TypeError):
        pass

    css_path = _THEMES_DIR / theme_name / "styles.css"
    if css_path.exists():
        return css_path.read_text()

    raise FileNotFoundError(f"Theme '{theme_name}' not found or missing styles.css")


def deck_hdrs(theme: str = "default") -> list:
    """Header elements shared between server and export."""
    from starhtml import Link, Script, Style, iconify_script

    return [
        Script(src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"),
        iconify_script(),
        Link(
            rel="stylesheet",
            href="https://fonts.googleapis.com/css2?family=Shantell+Sans:wght@400;700&display=swap",
        ),
        Style(get_theme_css(theme)),
    ]


def list_themes() -> list[str]:
    """List available theme names."""
    return [
        d.name
        for d in _THEMES_DIR.iterdir()
        if d.is_dir() and not d.name.startswith("_") and (d / "styles.css").exists()
    ]


def get_theme_metadata(theme_name: str = "default") -> dict:
    """Get metadata for a theme."""
    try:
        mod = import_module(f"stardeck.themes.{theme_name}")
        return {
            "name": getattr(mod, "NAME", theme_name),
            "description": getattr(mod, "DESCRIPTION", ""),
            "author": getattr(mod, "AUTHOR", ""),
            "version": getattr(mod, "VERSION", "1.0.0"),
        }
    except (ModuleNotFoundError, AttributeError):
        return {"name": theme_name, "description": "", "author": "", "version": "1.0.0"}
