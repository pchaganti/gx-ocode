"""Language-specific parsers and analysis tools."""

from .base import language_registry
from .python import PythonAnalyzer
from .typescript import TypeScriptAnalyzer
from .markdown import MarkdownAnalyzer
from .yaml import YAMLAnalyzer
from .terraform import TerraformAnalyzer

# Initialize analyzers
def _init_analyzers():
    """Initialize and register language analyzers."""
    # All analyzers are registered in their respective modules
    pass

_init_analyzers()

__all__ = [
    'language_registry', 
    'PythonAnalyzer', 
    'TypeScriptAnalyzer',
    'MarkdownAnalyzer',
    'YAMLAnalyzer', 
    'TerraformAnalyzer'
]
