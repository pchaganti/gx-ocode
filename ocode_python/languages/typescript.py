"""
TypeScript/JavaScript language analyzer.
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


class TypeScriptAnalyzer(LanguageAnalyzer):
    """TypeScript/JavaScript language analyzer."""

    def __init__(self):
        super().__init__()
        self.supported_extensions = {".ts", ".tsx", ".js", ".jsx"}

    @property
    def file_extensions(self) -> List[str]:
        """Return list of file extensions this analyzer handles."""
        return [".ts", ".tsx", ".js", ".jsx"]

    @property
    def comment_patterns(self) -> List[str]:
        """Return list of comment patterns for this language."""
        return ["//", "/*"]

    def can_analyze(self, file_path: Path) -> bool:
        """Check if this analyzer can handle the file."""
        return file_path.suffix.lower() in self.supported_extensions

    def extract_symbols(self, content: str) -> List[Symbol]:
        """Extract symbols from TypeScript/JavaScript code."""
        symbols = []

        # Extract functions
        symbols.extend(self._extract_functions(content))

        # Extract classes
        symbols.extend(self._extract_classes(content))

        # Extract interfaces (TypeScript)
        symbols.extend(self._extract_interfaces(content))

        # Extract types (TypeScript)
        symbols.extend(self._extract_types(content))

        # Extract variables and constants
        symbols.extend(self._extract_variables(content))

        # Extract enums
        symbols.extend(self._extract_enums(content))

        return symbols

    def _extract_functions(self, content: str) -> List[Symbol]:
        """Extract function definitions."""
        functions = []

        # Regular function declarations
        func_pattern = r"(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\([^)]*\)(?:\s*:\s*[^{]+)?\s*\{"  # noqa: E501
        for match in re.finditer(func_pattern, content, re.MULTILINE):
            line_num = content[: match.start()].count("\n") + 1
            functions.append(
                Symbol(
                    name=match.group(1),
                    type=SymbolType.FUNCTION,
                    line=line_num,
                    column=match.start() - content.rfind("\n", 0, match.start()),
                    visibility="public" if "export" in match.group(0) else "private",
                )
            )

        # Arrow functions assigned to variables
        arrow_pattern = r"(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*(?::\s*[^=]+)?\s*=>"  # noqa: E501
        for match in re.finditer(arrow_pattern, content, re.MULTILINE):
            line_num = content[: match.start()].count("\n") + 1
            functions.append(
                Symbol(
                    name=match.group(1),
                    type=SymbolType.FUNCTION,
                    line=line_num,
                    column=match.start() - content.rfind("\n", 0, match.start()),
                    visibility="public" if "export" in match.group(0) else "private",
                )
            )

        # Method definitions in classes
        method_pattern = r"(?:(?:public|private|protected)\s+)?(?:static\s+)?(?:async\s+)?(\w+)\s*\([^)]*\)(?:\s*:\s*[^{]+)?\s*\{"  # noqa: E501
        for match in re.finditer(method_pattern, content, re.MULTILINE):
            line_num = content[: match.start()].count("\n") + 1
            visibility = "private"
            if "public" in match.group(0):
                visibility = "public"
            elif "protected" in match.group(0):
                visibility = "protected"
            elif not match.group(1).startswith("_"):
                visibility = "public"

            functions.append(
                Symbol(
                    name=match.group(1),
                    type=SymbolType.METHOD,
                    line=line_num,
                    column=match.start() - content.rfind("\n", 0, match.start()),
                    visibility=visibility,
                )
            )

        return functions

    def _extract_classes(self, content: str) -> List[Symbol]:
        """Extract class definitions."""
        classes = []

        class_pattern = r"(?:export\s+)?(?:abstract\s+)?class\s+(\w+)(?:\s+extends\s+\w+)?(?:\s+implements\s+[\w,\s]+)?\s*\{"  # noqa: E501
        for match in re.finditer(class_pattern, content, re.MULTILINE):
            line_num = content[: match.start()].count("\n") + 1
            classes.append(
                Symbol(
                    name=match.group(1),
                    type=SymbolType.CLASS,
                    line=line_num,
                    column=match.start() - content.rfind("\n", 0, match.start()),
                    visibility="public" if "export" in match.group(0) else "private",
                )
            )

        return classes

    def _extract_interfaces(self, content: str) -> List[Symbol]:
        """Extract TypeScript interface definitions."""
        interfaces = []

        interface_pattern = (
            r"(?:export\s+)?interface\s+(\w+)(?:\s+extends\s+[\w,\s]+)?\s*\{"
        )
        for match in re.finditer(interface_pattern, content, re.MULTILINE):
            line_num = content[: match.start()].count("\n") + 1
            interfaces.append(
                Symbol(
                    name=match.group(1),
                    type=SymbolType.INTERFACE,
                    line=line_num,
                    column=match.start() - content.rfind("\n", 0, match.start()),
                    visibility="public" if "export" in match.group(0) else "private",
                )
            )

        return interfaces

    def _extract_types(self, content: str) -> List[Symbol]:
        """Extract TypeScript type definitions."""
        types = []

        type_pattern = r"(?:export\s+)?type\s+(\w+)\s*="
        for match in re.finditer(type_pattern, content, re.MULTILINE):
            line_num = content[: match.start()].count("\n") + 1
            types.append(
                Symbol(
                    name=match.group(1),
                    type=SymbolType.INTERFACE,
                    line=line_num,
                    column=match.start() - content.rfind("\n", 0, match.start()),
                    visibility="public" if "export" in match.group(0) else "private",
                )
            )

        return types

    def _extract_variables(self, content: str) -> List[Symbol]:
        """Extract variable and constant declarations."""
        variables = []

        # Variable declarations
        var_pattern = r"(?:export\s+)?(?:const|let|var)\s+(\w+)(?:\s*:\s*[^=]+)?\s*="
        for match in re.finditer(var_pattern, content, re.MULTILINE):
            line_num = content[: match.start()].count("\n") + 1
            is_const = "const" in match.group(0)
            symbol_type = SymbolType.CONSTANT if is_const else SymbolType.VARIABLE

            variables.append(
                Symbol(
                    name=match.group(1),
                    type=symbol_type,
                    line=line_num,
                    column=match.start() - content.rfind("\n", 0, match.start()),
                    visibility="public" if "export" in match.group(0) else "private",
                )
            )

        return variables

    def _extract_enums(self, content: str) -> List[Symbol]:
        """Extract TypeScript enum definitions."""
        enums = []

        enum_pattern = r"(?:export\s+)?(?:const\s+)?enum\s+(\w+)\s*\{"
        for match in re.finditer(enum_pattern, content, re.MULTILINE):
            line_num = content[: match.start()].count("\n") + 1
            enums.append(
                Symbol(
                    name=match.group(1),
                    type=SymbolType.ENUM,
                    line=line_num,
                    column=match.start() - content.rfind("\n", 0, match.start()),
                    visibility="public" if "export" in match.group(0) else "private",
                )
            )

        return enums

    def extract_imports(self, content: str) -> List[Import]:
        """Extract import statements."""
        imports = []

        # ES6 imports
        import_patterns = [
            r"import\s+(?:{[^}]+}|\w+|\*\s+as\s+\w+)\s+from\s+['\"]([^'\"]+)['\"]",
            r"import\s+['\"]([^'\"]+)['\"]",
            r"import\s*\(\s*['\"]([^'\"]+)['\"]\s*\)",  # Dynamic imports
        ]

        for pattern in import_patterns:
            for match in re.finditer(pattern, content, re.MULTILINE):
                module_name = match.group(1)
                line_num = content[: match.start()].count("\n") + 1

                imports.append(
                    Import(
                        module=module_name,
                        line=line_num,
                        is_relative=module_name.startswith("."),
                        alias=None,  # Could be enhanced to extract aliases
                    )
                )

        # CommonJS requires
        require_pattern = r"(?:const|let|var)\s+(?:{[^}]+}|\w+)\s*=\s*require\s*\(\s*['\"]([^'\"]+)['\"]\s*\)"  # noqa: E501
        for match in re.finditer(require_pattern, content, re.MULTILINE):
            module_name = match.group(1)
            line_num = content[: match.start()].count("\n") + 1

            imports.append(
                Import(
                    module=module_name,
                    line=line_num,
                    is_relative=module_name.startswith("."),
                    alias=None,
                )
            )

        return imports

    def calculate_metrics(self, content: str, symbols: List[Symbol]) -> CodeMetrics:
        """Calculate code metrics."""
        lines = content.split("\n")

        # Count different types of lines
        code_lines = 0
        comment_lines = 0
        blank_lines = 0

        in_block_comment = False

        for line in lines:
            stripped = line.strip()

            if not stripped:
                blank_lines += 1
            elif in_block_comment:
                comment_lines += 1
                if "*/" in stripped:
                    in_block_comment = False
            elif stripped.startswith("//"):
                comment_lines += 1
            elif stripped.startswith("/*"):
                comment_lines += 1
                if not stripped.endswith("*/"):
                    in_block_comment = True
            else:
                code_lines += 1

        # Calculate complexity (simplified)
        complexity = self._calculate_complexity(content)

        return CodeMetrics(
            lines_of_code=code_lines,
            cyclomatic_complexity=complexity,
            cognitive_complexity=complexity,
            maintainability_index=max(0, 171 - 5.2 * complexity - 0.23 * code_lines),
            function_count=len([s for s in symbols if s.type == SymbolType.FUNCTION]),
            class_count=len([s for s in symbols if s.type == SymbolType.CLASS]),
            max_nesting_depth=self._calculate_max_nesting_depth(content),
            comment_ratio=comment_lines / max(len(lines), 1),
        )

    def _calculate_complexity(self, content: str) -> int:
        """Calculate cyclomatic complexity."""
        complexity = 1  # Base complexity

        # Keywords that increase complexity
        complexity_keywords = [
            r"\bif\b",
            r"\belse\b",
            r"\bwhile\b",
            r"\bfor\b",
            r"\bdo\b",
            r"\bswitch\b",
            r"\bcase\b",
            r"\bcatch\b",
            r"\btry\b",
            r"\?\s*:",
            r"\|\|",
            r"\&\&",
        ]

        for keyword in complexity_keywords:
            complexity += len(re.findall(keyword, content))

        return complexity

    def parse_file(self, file_path: Path, content: str) -> AnalysisResult:
        """Parse a TypeScript/JavaScript file and extract symbols, imports, and metrics."""  # noqa: E501
        symbols = self.extract_symbols(content)
        imports = self.extract_imports(content)
        metrics = self.calculate_metrics(content, symbols)

        # Resolve dependencies from imports
        dependencies = self.resolve_dependencies(imports, file_path.parent)

        return AnalysisResult(
            file_path=file_path,
            language=(
                "typescript" if file_path.suffix in {".ts", ".tsx"} else "javascript"
            ),
            symbols=symbols,
            imports=imports,
            metrics=metrics,
            dependencies=dependencies,
            syntax_errors=[],
        )

    def _calculate_max_nesting_depth(self, content: str) -> int:
        """Calculate maximum nesting depth."""
        max_depth = 0
        current_depth = 0

        for line in content.split("\n"):
            stripped = line.strip()
            if not stripped:
                continue

            # Count opening and closing braces
            open_braces = line.count("{")
            close_braces = line.count("}")

            # Update current depth
            current_depth += open_braces - close_braces
            max_depth = max(max_depth, current_depth)

            # Ensure depth doesn't go negative
            current_depth = max(0, current_depth)

        return max_depth


# Register the analyzer
if __name__ != "__main__":
    ts_analyzer = TypeScriptAnalyzer()
    language_registry.register(ts_analyzer)
