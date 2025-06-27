"""
Enhanced UI components for OCode with theming support.
"""

import time
from typing import Any, Dict, List, Optional, Tuple

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn, TimeElapsedColumn
from rich.prompt import Confirm, Prompt
from rich.spinner import Spinner
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

from .theme import get_themed_console, theme_manager


class ThemedPanel:
    """Panel component with theme support."""

    @staticmethod
    def create(
        content: str,
        title: str = "",
        style: str = "panel.border",
        title_style: str = "panel.title",
        expand: bool = False,
        console: Optional[Console] = None,
    ) -> Panel:
        """Create a themed panel."""
        if console is None:
            console = get_themed_console()

        return Panel(content, title=title, border_style=style, expand=expand)

    @staticmethod
    def info(content: str, title: str = "ℹ️  Info") -> Panel:
        """Create an info panel."""
        return ThemedPanel.create(
            content, title=title, style="info", title_style="info"
        )

    @staticmethod
    def success(content: str, title: str = "✅ Success") -> Panel:
        """Create a success panel."""
        return ThemedPanel.create(
            content, title=title, style="success", title_style="success"
        )

    @staticmethod
    def warning(content: str, title: str = "⚠️  Warning") -> Panel:
        """Create a warning panel."""
        return ThemedPanel.create(
            content, title=title, style="warning", title_style="warning"
        )

    @staticmethod
    def error(content: str, title: str = "❌ Error") -> Panel:
        """Create an error panel."""
        return ThemedPanel.create(
            content, title=title, style="error", title_style="error"
        )


class ThemedTable:
    """Table component with theme support."""

    @staticmethod
    def create(
        title: str = "",
        header_style: str = "table.header",
        border_style: str = "muted",
        show_header: bool = True,
        show_lines: bool = False,
    ) -> Table:
        """Create a themed table."""
        return Table(
            title=title,
            header_style=header_style,
            border_style=border_style,
            show_header=show_header,
            show_lines=show_lines,
        )


class ThemedSyntax:
    """Syntax highlighter with theme support."""

    @staticmethod
    def create(
        code: str,
        lexer: str = "python",
        theme: str = "monokai",
        line_numbers: bool = False,
        word_wrap: bool = False,
        background_color: Optional[str] = None,
    ) -> Syntax:
        """Create themed syntax highlighting."""
        # Use theme background if not specified
        if background_color is None:
            active_theme = theme_manager.get_active_theme()
            background_color = active_theme.colors.background

        return Syntax(
            code,
            lexer,
            theme=theme,
            line_numbers=line_numbers,
            word_wrap=word_wrap,
            background_color=background_color,
        )


class StatusIndicator:
    """Status indicator with themed styling."""

    @staticmethod
    def loading(message: str = "Loading...") -> Text:
        """Create a loading status."""
        text = Text()
        text.append("⏳ ", style="status.loading")
        text.append(message, style="status.loading")
        return text

    @staticmethod
    def success(message: str = "Success") -> Text:
        """Create a success status."""
        text = Text()
        text.append("✅ ", style="status.success")
        text.append(message, style="status.success")
        return text

    @staticmethod
    def warning(message: str = "Warning") -> Text:
        """Create a warning status."""
        text = Text()
        text.append("⚠️  ", style="status.warning")
        text.append(message, style="status.warning")
        return text

    @staticmethod
    def error(message: str = "Error") -> Text:
        """Create an error status."""
        text = Text()
        text.append("❌ ", style="status.error")
        text.append(message, style="status.error")
        return text

    @staticmethod
    def info(message: str = "Info") -> Text:
        """Create an info status."""
        text = Text()
        text.append("ℹ️  ", style="info")
        text.append(message, style="info")
        return text


class ThemedProgress:
    """Progress indicator with theme support."""

    @staticmethod
    def create(description: str = "Working...") -> Progress:
        """Create a themed progress bar."""
        return Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(style="progress.bar", complete_style="success"),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=get_themed_console(),
        )


class ConversationRenderer:
    """Renders conversation messages with proper theming."""

    def __init__(self, console: Optional[Console] = None):
        self.console = console or get_themed_console()

    def render_user_message(self, content: str, timestamp: Optional[float] = None):
        """Render a user message."""
        header = Text()
        header.append("👤 ", style="primary")
        header.append("User", style="bold primary")

        if timestamp:
            time_str = time.strftime("%H:%M:%S", time.localtime(timestamp))
            header.append(f" [{time_str}]", style="muted")

        self.console.print(header)
        self.console.print(content, style="user_input")
        self.console.print()

    def render_ai_message(self, content: str, timestamp: Optional[float] = None):
        """Render an AI response message."""
        header = Text()
        header.append("🤖 ", style="accent")
        header.append("Assistant", style="bold accent")

        if timestamp:
            time_str = time.strftime("%H:%M:%S", time.localtime(timestamp))
            header.append(f" [{time_str}]", style="muted")

        self.console.print(header)

        # Render markdown if it looks like markdown
        if any(marker in content for marker in ["```", "**", "*", "#", "##"]):
            try:
                self.console.print(Markdown(content))
            except Exception:
                self.console.print(content, style="ai_response")
        else:
            self.console.print(content, style="ai_response")

        self.console.print()

    def render_tool_call(
        self, tool_name: str, args: Dict[str, Any], timestamp: Optional[float] = None
    ):
        """Render a tool call."""
        header = Text()
        header.append("🔧 ", style="secondary")
        header.append("Tool Call", style="bold secondary")

        if timestamp:
            time_str = time.strftime("%H:%M:%S", time.localtime(timestamp))
            header.append(f" [{time_str}]", style="muted")

        self.console.print(header)

        # Create tool call display
        tool_text = Text()
        tool_text.append(tool_name, style="bold tool_call")
        tool_text.append("(", style="tool_call")

        # Format arguments
        arg_parts = []
        for key, value in args.items():
            arg_text = Text()
            arg_text.append(key, style="bold tool_call")
            arg_text.append("=", style="tool_call")
            arg_text.append(repr(value), style="tool_call")
            arg_parts.append(arg_text)

        if arg_parts:
            for i, part in enumerate(arg_parts):
                if i > 0:
                    tool_text.append(", ", style="tool_call")
                tool_text.append_text(part)

        tool_text.append(")", style="tool_call")

        self.console.print(tool_text)
        self.console.print()

    def render_system_message(self, content: str, timestamp: Optional[float] = None):
        """Render a system message."""
        header = Text()
        header.append("⚙️  ", style="muted")
        header.append("System", style="bold muted")

        if timestamp:
            time_str = time.strftime("%H:%M:%S", time.localtime(timestamp))
            header.append(f" [{time_str}]", style="muted")

        self.console.print(header)
        self.console.print(content, style="muted")
        self.console.print()


class ThemeSelector:
    """Interactive theme selection component."""

    def __init__(self, console: Optional[Console] = None):
        self.console = console or get_themed_console()

    def show_theme_preview(self, theme_name: str):
        """Show a preview of a theme."""
        theme = theme_manager.get_theme(theme_name)
        if not theme:
            return

        # Temporarily switch to the theme for preview
        old_theme = theme_manager.get_active_theme()
        theme_manager.set_active_theme(theme_name)

        preview_console = theme_manager.get_console()

        # Create preview content
        preview_content = []

        preview_content.append(
            ThemedPanel.info(
                f"Theme: {theme.name}\n"
                f"Type: {theme.type.value}\n"
                f"Description: {theme.description}",
                title="Theme Info",
            )
        )

        # Show color samples
        sample_text = Text()
        sample_text.append("Primary ", style="primary")
        sample_text.append("Secondary ", style="secondary")
        sample_text.append("Accent ", style="accent")
        sample_text.append("Success ", style="success")
        sample_text.append("Warning ", style="warning")
        sample_text.append("Error ", style="error")
        sample_text.append("Info", style="info")

        preview_content.append(Panel(sample_text, title="Color Palette"))

        # Show syntax highlighting sample
        code_sample = '''def greet(name: str) -> str:
    """Return a greeting message."""
    # This is a comment
    return f"Hello, {name}!"

result = greet("World")
print(result)'''

        syntax = ThemedSyntax.create(code_sample, "python", line_numbers=True)
        preview_content.append(Panel(syntax, title="Syntax Highlighting"))

        # Display preview
        for content in preview_content:
            preview_console.print(content)
            preview_console.print()

        # Restore original theme
        theme_manager.set_active_theme(old_theme.name)

    def _build_theme_table(self) -> Tuple[Table, List[str]]:
        """Build theme selection table and return theme list."""
        themes = theme_manager.list_themes()
        # Group themes by type
        dark_themes = [t for t in themes if t.type.value == "dark"]
        light_themes = [t for t in themes if t.type.value == "light"]
        other_themes = [t for t in themes if t.type.value not in ["dark", "light"]]

        # Create selection table
        table = ThemedTable.create(title="Available Themes")
        table.add_column("Type", style="secondary")
        table.add_column("Name", style="primary")
        table.add_column("Description", style="default")

        theme_list = []

        # Add dark themes
        for theme in dark_themes:
            table.add_row("🌙 Dark", theme.name, theme.description)
            theme_list.append(theme.name)

        # Add light themes
        for theme in light_themes:
            table.add_row("☀️  Light", theme.name, theme.description)
            theme_list.append(theme.name)

        # Add other themes
        for theme in other_themes:
            icon = "🔍" if theme.type.value == "high_contrast" else "⚡"
            table.add_row(
                f"{icon} {theme.type.value.title()}", theme.name, theme.description
            )
            theme_list.append(theme.name)

        return table, theme_list

    def _handle_preview_command(self, choice: str, theme_list: List[str]) -> bool:
        """Handle preview command. Returns True if preview was shown."""
        if not choice.startswith("preview "):
            return False
        theme_name = choice[8:].strip()
        if theme_name in theme_list:
            self.show_theme_preview(theme_name)
        else:
            self.console.print(f"[error]Theme '{theme_name}' not found[/error]")
        return True

    def select_theme(self) -> Optional[str]:
        """Interactive theme selection."""
        table, theme_list = self._build_theme_table()
        self.console.print(table)
        self.console.print()

        # Get user selection
        while True:
            choice = Prompt.ask(
                "Select a theme name (or 'preview <name>' to preview)",
                console=self.console,
                default=theme_manager.get_active_theme().name,
            )

            # Handle preview command
            if self._handle_preview_command(choice, theme_list):
                continue

            # Handle theme selection
            if choice in theme_list:
                return choice

            # Handle exit commands
            if choice.lower() in ["quit", "exit", "cancel"]:
                return None

            self.console.print("[error]Please select a valid theme name[/error]")


class LoadingSpinner:
    """Themed loading spinner component."""

    def __init__(self, message: str = "Loading...", console: Optional[Console] = None):
        self.message = message
        self.console = console or get_themed_console()
        self.spinner = Spinner("dots", text=message, style="info")

    def __enter__(self):
        self.live = Live(self.spinner, console=self.console)
        self.live.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.live.stop()

    def update(self, message: str):
        """Update the spinner message."""
        self.message = message
        self.spinner.text = message


class ConfirmationDialog:
    """Themed confirmation dialog."""

    @staticmethod
    def ask(
        question: str, default: bool = True, console: Optional[Console] = None
    ) -> bool:
        """Ask for confirmation with theming."""
        if console is None:
            console = get_themed_console()

        return Confirm.ask(question, default=default, console=console)

    @staticmethod
    def ask_with_details(
        question: str,
        details: str,
        default: bool = True,
        console: Optional[Console] = None,
    ) -> bool:
        """Ask for confirmation with additional details."""
        if console is None:
            console = get_themed_console()

        # Show details panel
        console.print(ThemedPanel.warning(details, title="⚠️  Please Review"))
        console.print()

        return Confirm.ask(question, default=default, console=console)
