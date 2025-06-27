"""
Advanced theming system for OCode with syntax highlighting support.
"""

import os
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.theme import Theme as RichTheme


class ThemeType(Enum):
    """Theme type classification."""

    DARK = "dark"
    LIGHT = "light"
    HIGH_CONTRAST = "high_contrast"
    MINIMAL = "minimal"


@dataclass
class ColorScheme:
    """Color scheme definition for a theme."""

    # Base colors
    background: str
    foreground: str

    # UI colors
    primary: str
    secondary: str
    accent: str
    muted: str

    # Semantic colors
    success: str
    warning: str
    error: str
    info: str

    # Syntax highlighting colors
    keyword: str
    string: str
    number: str
    comment: str
    operator: str
    function: str
    variable: str
    type_name: str
    constant: str

    # Terminal colors
    black: str = "black"
    red: str = "red"
    green: str = "green"
    yellow: str = "yellow"
    blue: str = "blue"
    magenta: str = "magenta"
    cyan: str = "cyan"
    white: str = "white"


class Theme:
    """Represents a complete OCode theme with syntax highlighting and UI colors."""

    def __init__(
        self,
        name: str,
        theme_type: ThemeType,
        colors: ColorScheme,
        description: str = "",
    ):
        self.name = name
        self.type = theme_type
        self.colors = colors
        self.description = description
        self._rich_theme: Optional[RichTheme] = None

    def get_rich_theme(self) -> RichTheme:
        """Get Rich console theme for this OCode theme."""
        if self._rich_theme is None:
            self._rich_theme = RichTheme(
                {
                    # Base styles
                    "default": self.colors.foreground,
                    "primary": self.colors.primary,
                    "secondary": self.colors.secondary,
                    "accent": self.colors.accent,
                    "muted": self.colors.muted,
                    # Semantic styles
                    "success": self.colors.success,
                    "warning": self.colors.warning,
                    "error": self.colors.error,
                    "info": self.colors.info,
                    # Syntax highlighting
                    "code.keyword": f"bold {self.colors.keyword}",
                    "code.string": self.colors.string,
                    "code.number": self.colors.number,
                    "code.comment": f"italic {self.colors.comment}",
                    "code.operator": self.colors.operator,
                    "code.function": f"bold {self.colors.function}",
                    "code.variable": self.colors.variable,
                    "code.type": f"bold {self.colors.type_name}",
                    "code.constant": f"bold {self.colors.constant}",
                    # UI components
                    "panel.border": self.colors.muted,
                    "panel.title": f"bold {self.colors.primary}",
                    "table.header": f"bold {self.colors.primary}",
                    "progress.bar": self.colors.accent,
                    "progress.percentage": self.colors.info,
                    # Status indicators
                    "status.loading": self.colors.info,
                    "status.success": self.colors.success,
                    "status.warning": self.colors.warning,
                    "status.error": self.colors.error,
                    # Special UI elements
                    "prompt": f"bold {self.colors.primary}",
                    "user_input": self.colors.accent,
                    "ai_response": self.colors.foreground,
                    "tool_call": f"italic {self.colors.secondary}",
                    "file_path": f"underline {self.colors.info}",
                    "command": f"bold {self.colors.warning}",
                }
            )

        return self._rich_theme

    def to_dict(self) -> Dict[str, Any]:
        """Convert theme to dictionary for serialization."""
        return {
            "name": self.name,
            "type": self.type.value,
            "description": self.description,
            "colors": {
                "background": self.colors.background,
                "foreground": self.colors.foreground,
                "primary": self.colors.primary,
                "secondary": self.colors.secondary,
                "accent": self.colors.accent,
                "muted": self.colors.muted,
                "success": self.colors.success,
                "warning": self.colors.warning,
                "error": self.colors.error,
                "info": self.colors.info,
                "keyword": self.colors.keyword,
                "string": self.colors.string,
                "number": self.colors.number,
                "comment": self.colors.comment,
                "operator": self.colors.operator,
                "function": self.colors.function,
                "variable": self.colors.variable,
                "type_name": self.colors.type_name,
                "constant": self.colors.constant,
            },
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Theme":
        """Create theme from dictionary."""
        colors = ColorScheme(**data["colors"])
        return cls(
            name=data["name"],
            theme_type=ThemeType(data["type"]),
            colors=colors,
            description=data.get("description", ""),
        )


class ThemeManager:
    """Manages themes and provides theme switching capabilities."""

    def __init__(self):
        self._themes: Dict[str, Theme] = {}
        self._active_theme: Optional[Theme] = None
        self._load_builtin_themes()

    def _load_builtin_themes(self):
        """Load built-in themes."""
        for theme in create_default_themes():
            self._themes[theme.name] = theme

        # Set default theme
        self._active_theme = self._themes.get("default_dark")

    def register_theme(self, theme: Theme):
        """Register a new theme."""
        self._themes[theme.name] = theme

    def get_theme(self, name: str) -> Optional[Theme]:
        """Get theme by name."""
        return self._themes.get(name)

    def list_themes(self) -> List[Theme]:
        """List all available themes."""
        return list(self._themes.values())

    def list_themes_by_type(self, theme_type: ThemeType) -> List[Theme]:
        """List themes by type."""
        return [theme for theme in self._themes.values() if theme.type == theme_type]

    def set_active_theme(self, name: str) -> bool:
        """Set the active theme."""
        theme = self.get_theme(name)
        if theme:
            self._active_theme = theme
            return True
        return False

    def get_active_theme(self) -> Theme:
        """Get the currently active theme."""
        # Check for NO_COLOR environment variable
        if os.getenv("NO_COLOR"):
            minimal_theme = self._themes.get("minimal")
            if minimal_theme:
                return minimal_theme
            elif self._active_theme:
                return self._active_theme
            else:
                return self._themes["default_dark"]

        return self._active_theme or self._themes["default_dark"]

    def get_console(self, force_terminal: Optional[bool] = None) -> Console:
        """Get a Rich console with the active theme."""
        theme = self.get_active_theme()
        return Console(theme=theme.get_rich_theme(), force_terminal=force_terminal)


def create_default_themes() -> List[Theme]:
    """Create the built-in theme collection."""
    themes = []

    # Default Dark Theme
    themes.append(
        Theme(
            name="default_dark",
            theme_type=ThemeType.DARK,
            description="Default dark theme with balanced colors",
            colors=ColorScheme(
                background="#1e1e2e",
                foreground="#cdd6f4",
                primary="#89b4fa",
                secondary="#a6adc8",
                accent="#cba6f7",
                muted="#6c7086",
                success="#a6e3a1",
                warning="#f9e2af",
                error="#f38ba8",
                info="#89dceb",
                keyword="#cba6f7",
                string="#a6e3a1",
                number="#fab387",
                comment="#6c7086",
                operator="#f5c2e7",
                function="#89b4fa",
                variable="#cdd6f4",
                type_name="#f9e2af",
                constant="#fab387",
            ),
        )
    )

    # Default Light Theme
    themes.append(
        Theme(
            name="default_light",
            theme_type=ThemeType.LIGHT,
            description="Default light theme with muted colors",
            colors=ColorScheme(
                background="#fafafa",
                foreground="#3c3c43",
                primary="#3b82f6",
                secondary="#6b7280",
                accent="#8b5cf6",
                muted="#9ca3af",
                success="#059669",
                warning="#d97706",
                error="#dc2626",
                info="#0284c7",
                keyword="#8b5cf6",
                string="#059669",
                number="#d97706",
                comment="#9ca3af",
                operator="#f59e0b",
                function="#3b82f6",
                variable="#3c3c43",
                type_name="#d97706",
                constant="#dc2626",
            ),
        )
    )

    # GitHub Dark Theme
    themes.append(
        Theme(
            name="github_dark",
            theme_type=ThemeType.DARK,
            description="GitHub dark theme for familiarity",
            colors=ColorScheme(
                background="#24292e",
                foreground="#d1d5da",
                primary="#79b8ff",
                secondary="#959da5",
                accent="#b392f0",
                muted="#6a737d",
                success="#85e89d",
                warning="#ffab70",
                error="#f97583",
                info="#9ecbff",
                keyword="#f97583",
                string="#9ecbff",
                number="#79b8ff",
                comment="#6a737d",
                operator="#f97583",
                function="#b392f0",
                variable="#d1d5da",
                type_name="#ffab70",
                constant="#79b8ff",
            ),
        )
    )

    # GitHub Light Theme
    themes.append(
        Theme(
            name="github_light",
            theme_type=ThemeType.LIGHT,
            description="GitHub light theme for familiarity",
            colors=ColorScheme(
                background="#ffffff",
                foreground="#24292e",
                primary="#0366d6",
                secondary="#586069",
                accent="#6f42c1",
                muted="#6a737d",
                success="#28a745",
                warning="#ffd33d",
                error="#d73a49",
                info="#0366d6",
                keyword="#d73a49",
                string="#032f62",
                number="#005cc5",
                comment="#6a737d",
                operator="#d73a49",
                function="#6f42c1",
                variable="#24292e",
                type_name="#005cc5",
                constant="#005cc5",
            ),
        )
    )

    # Dracula Theme
    themes.append(
        Theme(
            name="dracula",
            theme_type=ThemeType.DARK,
            description="Popular Dracula color scheme",
            colors=ColorScheme(
                background="#282a36",
                foreground="#f8f8f2",
                primary="#8be9fd",
                secondary="#6272a4",
                accent="#bd93f9",
                muted="#6272a4",
                success="#50fa7b",
                warning="#f1fa8c",
                error="#ff5555",
                info="#8be9fd",
                keyword="#ff79c6",
                string="#f1fa8c",
                number="#bd93f9",
                comment="#6272a4",
                operator="#ff79c6",
                function="#50fa7b",
                variable="#f8f8f2",
                type_name="#8be9fd",
                constant="#bd93f9",
            ),
        )
    )

    # High Contrast Theme
    themes.append(
        Theme(
            name="high_contrast",
            theme_type=ThemeType.HIGH_CONTRAST,
            description="High contrast theme for accessibility",
            colors=ColorScheme(
                background="#000000",
                foreground="#ffffff",
                primary="#00ffff",
                secondary="#c0c0c0",
                accent="#ffff00",
                muted="#808080",
                success="#00ff00",
                warning="#ffaa00",
                error="#ff0000",
                info="#00ffff",
                keyword="#ffff00",
                string="#00ff00",
                number="#00ffff",
                comment="#808080",
                operator="#ffff00",
                function="#00ffff",
                variable="#ffffff",
                type_name="#ffaa00",
                constant="#ff0000",
            ),
        )
    )

    # Minimal Theme (no colors)
    themes.append(
        Theme(
            name="minimal",
            theme_type=ThemeType.MINIMAL,
            description="Minimal theme with no colors for maximum compatibility",
            colors=ColorScheme(
                background="default",
                foreground="default",
                primary="default",
                secondary="default",
                accent="bold",
                muted="dim",
                success="default",
                warning="default",
                error="default",
                info="default",
                keyword="bold",
                string="default",
                number="default",
                comment="dim",
                operator="default",
                function="bold",
                variable="default",
                type_name="default",
                constant="default",
            ),
        )
    )

    # Monokai Theme
    themes.append(
        Theme(
            name="monokai",
            theme_type=ThemeType.DARK,
            description="Popular Monokai color scheme",
            colors=ColorScheme(
                background="#272822",
                foreground="#f8f8f2",
                primary="#66d9ef",
                secondary="#75715e",
                accent="#ae81ff",
                muted="#75715e",
                success="#a6e22e",
                warning="#e6db74",
                error="#f92672",
                info="#66d9ef",
                keyword="#f92672",
                string="#e6db74",
                number="#ae81ff",
                comment="#75715e",
                operator="#f92672",
                function="#a6e22e",
                variable="#f8f8f2",
                type_name="#66d9ef",
                constant="#ae81ff",
            ),
        )
    )

    return themes


# Global theme manager instance
theme_manager = ThemeManager()


def get_themed_console(force_terminal: Optional[bool] = None) -> Console:
    """Get a console with the current theme applied."""
    return theme_manager.get_console(force_terminal=force_terminal)
