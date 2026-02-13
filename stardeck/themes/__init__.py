"""StarDeck theme system.

Themes are directories containing CSS files and metadata.
Inspired by ShadCN's approach - themes live in your codebase and can be customized.

Structure:
    stardeck/themes/
    ├── __init__.py      # This file - theme loading
    ├── default/
    │   ├── __init__.py  # Theme metadata
    │   └── styles.css   # Theme styles
    └── dark/
        ├── __init__.py
        └── styles.css
"""

from importlib import resources
from pathlib import Path


def get_theme_css(theme_name: str = "default") -> str:
    """Load CSS for a theme by name.

    Args:
        theme_name: Name of the theme directory (e.g., "default", "dark")

    Returns:
        CSS content as a string

    Raises:
        FileNotFoundError: If theme or styles.css doesn't exist
    """
    # Try to load from package resources first
    try:
        theme_package = f"stardeck.themes.{theme_name}"
        css_file = resources.files(theme_package).joinpath("styles.css")
        return css_file.read_text()
    except (ModuleNotFoundError, FileNotFoundError, TypeError):
        pass

    # Fallback: try loading from filesystem (for development)
    themes_dir = Path(__file__).parent
    css_path = themes_dir / theme_name / "styles.css"
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
    """List available theme names.

    Returns:
        List of theme directory names
    """
    themes_dir = Path(__file__).parent
    return [
        d.name
        for d in themes_dir.iterdir()
        if d.is_dir() and not d.name.startswith("_") and (d / "styles.css").exists()
    ]


def get_theme_metadata(theme_name: str = "default") -> dict:
    """Get metadata for a theme.

    Args:
        theme_name: Name of the theme

    Returns:
        Dict with theme metadata (name, description, author, etc.)
    """
    try:
        theme_module = __import__(
            f"stardeck.themes.{theme_name}", fromlist=["NAME", "DESCRIPTION"]
        )
        return {
            "name": getattr(theme_module, "NAME", theme_name),
            "description": getattr(theme_module, "DESCRIPTION", ""),
            "author": getattr(theme_module, "AUTHOR", ""),
            "version": getattr(theme_module, "VERSION", "1.0.0"),
        }
    except (ModuleNotFoundError, AttributeError):
        return {"name": theme_name, "description": "", "author": "", "version": "1.0.0"}
