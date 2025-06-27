"""
YAML language analyzer.
"""

import re
from pathlib import Path
from typing import List

from .base import (
    AnalysisResult,
    CodeMetrics,
    Import,
    LanguageAnalyzer,
    Symbol,
    SymbolType,
    language_registry,
)


class YAMLAnalyzer(LanguageAnalyzer):
    """YAML language analyzer."""

    @property
    def file_extensions(self) -> List[str]:
        """Return list of file extensions this analyzer handles."""
        return [".yaml", ".yml"]

    @property
    def comment_patterns(self) -> List[str]:
        """Return list of comment patterns for this language."""
        return ["#"]

    def extract_symbols(self, content: str) -> List[Symbol]:
        """Extract symbols from YAML content."""
        symbols = []

        # Extract top-level keys
        symbols.extend(self._extract_keys(content))

        # Extract specific YAML structures
        symbols.extend(self._extract_anchors_and_aliases(content))

        return symbols

    def _extract_keys(self, content: str) -> List[Symbol]:
        """Extract YAML keys as symbols."""
        keys = []
        lines = content.split("\n")

        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()

            # Skip comments and empty lines
            if not stripped or stripped.startswith("#"):
                continue

            # Extract keys (key: value or key:)
            key_match = re.match(r"^(\s*)([a-zA-Z_][a-zA-Z0 - 9_-]*)\s*:\s*(.*)$", line)
            if key_match:
                indent = key_match.group(1)
                key = key_match.group(2)
                value = key_match.group(3).strip()

                # Determine indentation level
                indent_level = len(indent) // 2  # Assuming 2-space indentation

                # Determine symbol type based on value
                symbol_type = SymbolType.VARIABLE
                if not value or value.startswith(("|", ">")):
                    # Multi-line value or no value - likely a section
                    symbol_type = SymbolType.NAMESPACE
                elif value.startswith("[") or value.startswith("{"):
                    # Inline array/object
                    symbol_type = SymbolType.VARIABLE

                keys.append(
                    Symbol(
                        name=key,
                        type=symbol_type,
                        line=line_num,
                        column=len(indent),
                        scope=f"level_{indent_level}",
                        visibility="public",
                    )
                )

            # Extract array items with keys
            array_key_match = re.match(
                r"^(\s*)-\s*([a-zA-Z_][a-zA-Z0 - 9_-]*)\s*:\s*(.*)$", line
            )
            if array_key_match:
                indent = array_key_match.group(1)
                key = array_key_match.group(2)

                keys.append(
                    Symbol(
                        name=key,
                        type=SymbolType.VARIABLE,
                        line=line_num,
                        column=len(indent) + 2,  # Account for "- "
                        scope="array_item",
                        visibility="public",
                    )
                )

        return keys

    def _extract_anchors_and_aliases(self, content: str) -> List[Symbol]:
        """Extract YAML anchors (&) and aliases (*)."""
        anchors_aliases = []

        # Extract anchors (&anchor)
        anchor_pattern = r"&([a-zA-Z_][a-zA-Z0 - 9_-]*)"
        for match in re.finditer(anchor_pattern, content):
            line_num = content[: match.start()].count("\n") + 1
            anchor_name = match.group(1)

            anchors_aliases.append(
                Symbol(
                    name=anchor_name,
                    type=SymbolType.CONSTANT,  # Using constant for anchors
                    line=line_num,
                    column=match.start() - content.rfind("\n", 0, match.start()),
                    scope="anchor",
                    visibility="public",
                )
            )

        # Extract aliases (*alias)
        alias_pattern = r"\*([a-zA-Z_][a-zA-Z0 - 9_-]*)"
        for match in re.finditer(alias_pattern, content):
            line_num = content[: match.start()].count("\n") + 1
            alias_name = match.group(1)

            anchors_aliases.append(
                Symbol(
                    name=alias_name,
                    type=SymbolType.VARIABLE,  # Using variable for aliases
                    line=line_num,
                    column=match.start() - content.rfind("\n", 0, match.start()),
                    scope="alias",
                    visibility="public",
                )
            )

        return anchors_aliases

    def extract_imports(self, content: str) -> List[Import]:
        """Extract import-like references from YAML."""
        imports = []

        # Look for file references in values
        file_patterns = [
            r'(?:file|path|include|template|source)\s*:\s*["\']?([^"\'\s]+\.[a-zA-Z0 - 9]+)["\']?',  # noqa: E501
            r'["\']([^"\']*\.(yaml|yml|json|xml|properties|env))["\']',
        ]

        for pattern in file_patterns:
            for match in re.finditer(pattern, content, re.IGNORECASE):
                line_num = content[: match.start()].count("\n") + 1
                file_path = match.group(1)

                # Skip URLs
                if not file_path.startswith(("http://", "https://", "ftp://")):
                    imports.append(
                        Import(
                            module=file_path,
                            line=line_num,
                            is_relative=not file_path.startswith("/"),
                            alias=None,
                        )
                    )

        # Docker image references
        image_pattern = r'image\s*:\s*["\']?([^"\'\s]+)["\']?'
        for match in re.finditer(image_pattern, content, re.IGNORECASE):
            line_num = content[: match.start()].count("\n") + 1
            image_name = match.group(1)

            # Only include if it looks like a real image reference
            if "/" in image_name or ":" in image_name:
                imports.append(
                    Import(
                        module=image_name, line=line_num, is_relative=False, alias=None
                    )
                )

        return imports

    def calculate_metrics(self, content: str, symbols: List[Symbol]) -> CodeMetrics:
        """Calculate YAML-specific metrics."""
        lines = content.split("\n")

        # Count different types of lines
        code_lines = 0
        comment_lines = 0
        blank_lines = 0

        for line in lines:
            stripped = line.strip()
            if not stripped:
                blank_lines += 1
            elif stripped.startswith("#"):
                comment_lines += 1
            else:
                code_lines += 1

        # Calculate nesting depth
        max_depth = 0
        for line in lines:
            if line.strip() and not line.strip().startswith("#"):
                # Count leading spaces (assuming 2-space indentation)
                leading_spaces = len(line) - len(line.lstrip())
                depth = leading_spaces // 2
                max_depth = max(max_depth, depth)

        # Count different symbol types (currently unused but kept for future use)
        # _namespace_count = len([s for s in symbols if s.type == SymbolType.NAMESPACE])
        # _variable_count = len([s for s in symbols if s.type == SymbolType.VARIABLE])

        return CodeMetrics(
            lines_of_code=code_lines,
            cyclomatic_complexity=1,  # YAML is declarative, minimal complexity
            cognitive_complexity=max_depth,  # Use nesting depth as cognitive complexity
            maintainability_index=100 - max_depth * 5,  # Simple heuristic
            function_count=0,  # No functions in YAML
            class_count=0,  # No classes in YAML
            max_nesting_depth=max_depth,
            comment_ratio=comment_lines / max(len(lines), 1),
        )

    def parse_file(self, file_path: Path, content: str) -> AnalysisResult:
        """Parse a YAML file and extract symbols, imports, and metrics."""
        symbols = self.extract_symbols(content)
        imports = self.extract_imports(content)
        metrics = self.calculate_metrics(content, symbols)

        # Resolve dependencies from imports
        dependencies = self.resolve_dependencies(imports, file_path.parent)

        return AnalysisResult(
            file_path=file_path,
            language="yaml",
            symbols=symbols,
            imports=imports,
            metrics=metrics,
            dependencies=dependencies,
            syntax_errors=[],
        )


# Register the analyzer
if __name__ != "__main__":
    yaml_analyzer = YAMLAnalyzer()
    language_registry.register(yaml_analyzer)
