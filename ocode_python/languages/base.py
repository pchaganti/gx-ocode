"""
Base classes for language-specific analysis.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


class SymbolType(Enum):
    """Types of code symbols."""

    FUNCTION = "function"
    CLASS = "class"
    VARIABLE = "variable"
    CONSTANT = "constant"
    MODULE = "module"
    INTERFACE = "interface"
    ENUM = "enum"
    STRUCT = "struct"
    METHOD = "method"
    PROPERTY = "property"
    NAMESPACE = "namespace"


@dataclass
class Symbol:
    """Represents a code symbol."""

    name: str
    type: SymbolType
    line: int
    column: int
    end_line: Optional[int] = None
    end_column: Optional[int] = None
    scope: Optional[str] = None
    visibility: Optional[str] = None  # public, private, protected
    parameters: Optional[List[Dict[str, Any]]] = None
    return_type: Optional[str] = None
    docstring: Optional[str] = None
    decorators: Optional[List[str]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert symbol to dictionary representation.

        Returns:
            Dictionary containing all non-None symbol attributes.
        """
        result: Dict[str, Any] = {
            "name": self.name,
            "type": self.type.value,
            "line": self.line,
            "column": self.column,
        }

        if self.end_line is not None:
            result["end_line"] = self.end_line
        if self.end_column is not None:
            result["end_column"] = self.end_column
        if self.scope:
            result["scope"] = self.scope
        if self.visibility:
            result["visibility"] = self.visibility
        if self.parameters is not None:
            result["parameters"] = self.parameters
        if self.return_type is not None:
            result["return_type"] = self.return_type
        if self.docstring is not None:
            result["docstring"] = self.docstring
        if self.decorators is not None:
            result["decorators"] = self.decorators

        return result


@dataclass
class Import:
    """Represents an import statement."""

    module: str
    alias: Optional[str] = None
    items: Optional[List[str]] = None  # For "from X import Y, Z"
    line: int = 0
    is_relative: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert import to dictionary representation.

        Returns:
            Dictionary containing all import attributes.
        """
        return {
            "module": self.module,
            "alias": self.alias,
            "items": self.items,
            "line": self.line,
            "is_relative": self.is_relative,
        }


@dataclass
class CodeMetrics:
    """Code complexity and quality metrics."""

    lines_of_code: int = 0
    cyclomatic_complexity: int = 0
    cognitive_complexity: int = 0
    maintainability_index: float = 0.0
    function_count: int = 0
    class_count: int = 0
    max_nesting_depth: int = 0
    comment_ratio: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary representation.

        Returns:
            Dictionary containing all code metric values.
        """
        return {
            "lines_of_code": self.lines_of_code,
            "cyclomatic_complexity": self.cyclomatic_complexity,
            "cognitive_complexity": self.cognitive_complexity,
            "maintainability_index": self.maintainability_index,
            "function_count": self.function_count,
            "class_count": self.class_count,
            "max_nesting_depth": self.max_nesting_depth,
            "comment_ratio": self.comment_ratio,
        }


@dataclass
class AnalysisResult:
    """Complete analysis result for a source file."""

    file_path: Path
    language: str
    symbols: List[Symbol]
    imports: List[Import]
    metrics: CodeMetrics
    dependencies: Set[str]
    syntax_errors: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        """Convert analysis result to dictionary representation.

        Returns:
            Dictionary containing all analysis data in serializable format.
        """
        return {
            "file_path": str(self.file_path),
            "language": self.language,
            "symbols": [s.to_dict() for s in self.symbols],
            "imports": [i.to_dict() for i in self.imports],
            "metrics": self.metrics.to_dict(),
            "dependencies": list(self.dependencies),
            "syntax_errors": self.syntax_errors,
        }


class LanguageAnalyzer(ABC):
    """
    Base class for language-specific code analyzers.

    Each language implementation should inherit from this class
    and implement the required methods.
    """

    def __init__(self):
        """Initialize language analyzer.

        Sets the language name based on the class name.
        """
        self.language = self.__class__.__name__.lower().replace("analyzer", "")

    @property
    @abstractmethod
    def file_extensions(self) -> List[str]:
        """Return list of file extensions this analyzer handles.

        Returns:
            List of file extensions including the dot (e.g., ['.py', '.pyw']).
        """
        pass

    @property
    @abstractmethod
    def comment_patterns(self) -> List[str]:
        """Return list of comment patterns for this language.

        Returns:
            List of strings that indicate the start of a comment line.
        """
        pass

    @abstractmethod
    def parse_file(self, file_path: Path, content: str) -> AnalysisResult:
        """
        Parse a source file and extract symbols, imports, and metrics.

        Args:
            file_path: Path to the source file
            content: File content as string

        Returns:
            AnalysisResult with extracted information
        """
        pass

    @abstractmethod
    def extract_symbols(self, content: str) -> List[Symbol]:
        """Extract symbols from source code.

        Args:
            content: Source code content as string.

        Returns:
            List of Symbol objects found in the code.
        """
        pass

    @abstractmethod
    def extract_imports(self, content: str) -> List[Import]:
        """Extract import statements from source code.

        Args:
            content: Source code content as string.

        Returns:
            List of Import objects representing all imports in the code.
        """
        pass

    def calculate_metrics(self, content: str, symbols: List[Symbol]) -> CodeMetrics:
        """Calculate code metrics.

        Args:
            content: Source code content as string.
            symbols: List of extracted symbols.

        Returns:
            CodeMetrics object with calculated complexity and quality metrics.
        """
        lines = content.split("\n")

        # Basic metrics
        lines_of_code = len(
            [line for line in lines if line.strip() and not self._is_comment_line(line)]
        )
        comment_lines = len([line for line in lines if self._is_comment_line(line)])

        comment_ratio = comment_lines / max(len(lines), 1)

        # Count symbols by type
        function_count = len([s for s in symbols if s.type == SymbolType.FUNCTION])
        class_count = len([s for s in symbols if s.type == SymbolType.CLASS])

        # Simple cyclomatic complexity (count decision points)
        cyclomatic_complexity = self._calculate_cyclomatic_complexity(content)

        # Max nesting depth
        max_nesting_depth = self._calculate_max_nesting_depth(content)

        return CodeMetrics(
            lines_of_code=lines_of_code,
            cyclomatic_complexity=cyclomatic_complexity,
            cognitive_complexity=cyclomatic_complexity,  # Simplified
            maintainability_index=max(
                0, 171 - 5.2 * cyclomatic_complexity - 0.23 * lines_of_code
            ),
            function_count=function_count,
            class_count=class_count,
            max_nesting_depth=max_nesting_depth,
            comment_ratio=comment_ratio,
        )

    def _is_comment_line(self, line: str) -> bool:
        """Check if line is a comment.

        Args:
            line: Single line of code.

        Returns:
            True if the line is a comment, False otherwise.
        """
        stripped = line.strip()
        for pattern in self.comment_patterns:
            if stripped.startswith(pattern):
                return True
        return False

    def _calculate_cyclomatic_complexity(self, content: str) -> int:
        """Calculate cyclomatic complexity by counting decision points.

        This is a simplified implementation that counts control flow keywords.

        Args:
            content: Source code content.

        Returns:
            Estimated cyclomatic complexity value.
        """
        # This is a simplified implementation
        decision_keywords = [
            "if",
            "elif",
            "else",
            "for",
            "while",
            "try",
            "except",
            "case",
            "switch",
        ]
        complexity = 1  # Base complexity

        for line in content.split("\n"):
            stripped = line.strip()
            for keyword in decision_keywords:
                if f" {keyword} " in f" {stripped} " or stripped.startswith(
                    f"{keyword} "
                ):
                    complexity += 1

        return complexity

    def _calculate_max_nesting_depth(self, content: str) -> int:
        """Calculate maximum nesting depth.

        Estimates nesting depth based on indentation levels.

        Args:
            content: Source code content.

        Returns:
            Maximum indentation depth found in the code.
        """
        # Simplified implementation counting indentation
        max_depth = 0
        current_depth = 0

        for line in content.split("\n"):
            if line.strip():
                # Count leading whitespace
                indent = len(line) - len(line.lstrip())
                # Assume 4 spaces or 1 tab per level
                if "\t" in line:
                    depth = line.count("\t")
                else:
                    depth = indent // 4

                current_depth = depth
                max_depth = max(max_depth, current_depth)

        return max_depth

    def resolve_dependencies(
        self, imports: List[Import], project_root: Path
    ) -> Set[str]:
        """
        Resolve import dependencies to actual files in the project.

        Args:
            imports: List of import statements
            project_root: Project root directory

        Returns:
            Set of resolved dependency file paths
        """
        dependencies = set()

        for imp in imports:
            # Try to resolve import to actual file
            resolved = self._resolve_import_to_file(imp, project_root)
            if resolved:
                dependencies.add(resolved)

        return dependencies

    def _resolve_import_to_file(
        self, import_stmt: Import, project_root: Path
    ) -> Optional[str]:
        """
        Resolve a single import statement to a file path.

        This is a simplified implementation that can be overridden by language-specific analyzers.  # noqa: E501
        """
        module_parts = import_stmt.module.split(".")

        # Try different file extensions
        for ext in self.file_extensions:
            # Try as direct file
            file_path = project_root
            for part in module_parts:
                file_path = file_path / part

            candidate = file_path.with_suffix(ext)
            if candidate.exists():
                return str(candidate.relative_to(project_root))

            # Try as package (with __init__ file)
            init_file = file_path / f"__init__{ext}"
            if init_file.exists():
                return str(init_file.relative_to(project_root))

        return None

    def can_analyze(self, file_path: Path) -> bool:
        """Check if this analyzer can handle the given file.

        Args:
            file_path: Path to the file to check.

        Returns:
            True if the file extension is supported by this analyzer.
        """
        return file_path.suffix.lower() in self.file_extensions


class LanguageRegistry:
    """Registry for language analyzers."""

    def __init__(self):
        """Initialize language registry.

        Creates empty dictionaries for analyzers and extension mappings.
        """
        self.analyzers: Dict[str, LanguageAnalyzer] = {}
        self.extension_map: Dict[str, str] = {}

    def register(self, analyzer: LanguageAnalyzer):
        """Register a language analyzer.

        Args:
            analyzer: LanguageAnalyzer instance to register.
        """
        self.analyzers[analyzer.language] = analyzer

        # Map file extensions to language
        for ext in analyzer.file_extensions:
            self.extension_map[ext.lower()] = analyzer.language

    def get_analyzer(self, language: str) -> Optional[LanguageAnalyzer]:
        """Get analyzer by language name.

        Args:
            language: Name of the programming language.

        Returns:
            LanguageAnalyzer instance if found, None otherwise.
        """
        return self.analyzers.get(language)

    def get_analyzer_for_file(self, file_path: Path) -> Optional[LanguageAnalyzer]:
        """Get appropriate analyzer for a file.

        Args:
            file_path: Path to the file.

        Returns:
            LanguageAnalyzer instance if file type is supported, None otherwise.
        """
        ext = file_path.suffix.lower()
        language = self.extension_map.get(ext)

        if language:
            return self.analyzers.get(language)

        return None

    def get_supported_languages(self) -> List[str]:
        """Get list of supported languages.

        Returns:
            List of registered language names.
        """
        return list(self.analyzers.keys())

    def get_supported_extensions(self) -> List[str]:
        """Get list of supported file extensions.

        Returns:
            List of file extensions that can be analyzed.
        """
        return list(self.extension_map.keys())


# Create global registry instance
language_registry = LanguageRegistry()
