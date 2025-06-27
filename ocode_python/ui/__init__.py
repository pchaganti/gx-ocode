"""
UI components and theming system for OCode.
"""

from .theme import Theme, ThemeManager, create_default_themes
from .components import (
    ThemedPanel, ThemedTable, ThemedSyntax, StatusIndicator,
    ThemedProgress, ConversationRenderer, ThemeSelector,
    LoadingSpinner, ConfirmationDialog
)

__all__ = [
    "Theme",
    "ThemeManager",
    "create_default_themes",
    "ThemedPanel",
    "ThemedTable",
    "ThemedSyntax",
    "StatusIndicator",
    "ThemedProgress",
    "ConversationRenderer",
    "ThemeSelector",
    "LoadingSpinner",
    "ConfirmationDialog"
]
