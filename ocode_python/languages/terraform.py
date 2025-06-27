"""
Terraform/HCL language analyzer.
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


class TerraformAnalyzer(LanguageAnalyzer):
    """Terraform/HCL language analyzer."""

    @property
    def file_extensions(self) -> List[str]:
        """Return list of file extensions this analyzer handles."""
        return [".tf", ".tfvars", ".hcl"]

    @property
    def comment_patterns(self) -> List[str]:
        """Return list of comment patterns for this language."""
        return ["#", "//", "/*"]

    def extract_symbols(self, content: str) -> List[Symbol]:
        """Extract symbols from Terraform/HCL content."""
        symbols = []

        # Extract resource blocks
        symbols.extend(self._extract_resources(content))

        # Extract data blocks
        symbols.extend(self._extract_data_sources(content))

        # Extract variable declarations
        symbols.extend(self._extract_variables(content))

        # Extract output declarations
        symbols.extend(self._extract_outputs(content))

        # Extract provider blocks
        symbols.extend(self._extract_providers(content))

        # Extract module blocks
        symbols.extend(self._extract_modules(content))

        # Extract locals blocks
        symbols.extend(self._extract_locals(content))

        return symbols

    def _extract_resources(self, content: str) -> List[Symbol]:
        """Extract Terraform resource blocks."""
        resources = []

        # Pattern: resource "type" "name" {
        resource_pattern = r'resource\s+"([^"]+)"\s+"([^"]+)"\s*\{'
        for match in re.finditer(resource_pattern, content, re.MULTILINE):
            line_num = content[: match.start()].count("\n") + 1
            resource_type = match.group(1)
            resource_name = match.group(2)

            resources.append(
                Symbol(
                    name=f"{resource_type}.{resource_name}",
                    type=SymbolType.CLASS,  # Using class for resources
                    line=line_num,
                    column=match.start() - content.rfind("\n", 0, match.start()),
                    scope="resource",
                    visibility="public",
                )
            )

        return resources

    def _extract_data_sources(self, content: str) -> List[Symbol]:
        """Extract Terraform data source blocks."""
        data_sources = []

        # Pattern: data "type" "name" {
        data_pattern = r'data\s+"([^"]+)"\s+"([^"]+)"\s*\{'
        for match in re.finditer(data_pattern, content, re.MULTILINE):
            line_num = content[: match.start()].count("\n") + 1
            data_type = match.group(1)
            data_name = match.group(2)

            data_sources.append(
                Symbol(
                    name=f"data.{data_type}.{data_name}",
                    type=SymbolType.VARIABLE,  # Using variable for data sources
                    line=line_num,
                    column=match.start() - content.rfind("\n", 0, match.start()),
                    scope="data",
                    visibility="public",
                )
            )

        return data_sources

    def _extract_variables(self, content: str) -> List[Symbol]:
        """Extract Terraform variable declarations."""
        variables = []

        # Pattern: variable "name" {
        var_pattern = r'variable\s+"([^"]+)"\s*\{'
        for match in re.finditer(var_pattern, content, re.MULTILINE):
            line_num = content[: match.start()].count("\n") + 1
            var_name = match.group(1)

            variables.append(
                Symbol(
                    name=f"var.{var_name}",
                    type=SymbolType.VARIABLE,
                    line=line_num,
                    column=match.start() - content.rfind("\n", 0, match.start()),
                    scope="variable",
                    visibility="public",
                )
            )

        return variables

    def _extract_outputs(self, content: str) -> List[Symbol]:
        """Extract Terraform output declarations."""
        outputs = []

        # Pattern: output "name" {
        output_pattern = r'output\s+"([^"]+)"\s*\{'
        for match in re.finditer(output_pattern, content, re.MULTILINE):
            line_num = content[: match.start()].count("\n") + 1
            output_name = match.group(1)

            outputs.append(
                Symbol(
                    name=output_name,
                    type=SymbolType.PROPERTY,  # Using property for outputs
                    line=line_num,
                    column=match.start() - content.rfind("\n", 0, match.start()),
                    scope="output",
                    visibility="public",
                )
            )

        return outputs

    def _extract_providers(self, content: str) -> List[Symbol]:
        """Extract Terraform provider blocks."""
        providers = []

        # Pattern: provider "name" {
        provider_pattern = r'provider\s+"([^"]+)"\s*\{'
        for match in re.finditer(provider_pattern, content, re.MULTILINE):
            line_num = content[: match.start()].count("\n") + 1
            provider_name = match.group(1)

            providers.append(
                Symbol(
                    name=provider_name,
                    type=SymbolType.MODULE,  # Using module for providers
                    line=line_num,
                    column=match.start() - content.rfind("\n", 0, match.start()),
                    scope="provider",
                    visibility="public",
                )
            )

        return providers

    def _extract_modules(self, content: str) -> List[Symbol]:
        """Extract Terraform module blocks."""
        modules = []

        # Pattern: module "name" {
        module_pattern = r'module\s+"([^"]+)"\s*\{'
        for match in re.finditer(module_pattern, content, re.MULTILINE):
            line_num = content[: match.start()].count("\n") + 1
            module_name = match.group(1)

            modules.append(
                Symbol(
                    name=f"module.{module_name}",
                    type=SymbolType.MODULE,
                    line=line_num,
                    column=match.start() - content.rfind("\n", 0, match.start()),
                    scope="module",
                    visibility="public",
                )
            )

        return modules

    def _extract_locals(self, content: str) -> List[Symbol]:
        """Extract Terraform locals blocks."""
        locals_vars = []

        # Pattern: locals { ... }
        locals_pattern = r"locals\s*\{([^}]*)\}"
        for match in re.finditer(locals_pattern, content, re.DOTALL):
            line_num = content[: match.start()].count("\n") + 1
            locals_content = match.group(1)

            # Extract individual local variables
            local_var_pattern = r"([a-zA-Z_][a-zA-Z0 - 9_]*)\s*="
            for var_match in re.finditer(local_var_pattern, locals_content):
                var_name = var_match.group(1)
                var_line = line_num + locals_content[: var_match.start()].count("\n")

                locals_vars.append(
                    Symbol(
                        name=f"local.{var_name}",
                        type=SymbolType.CONSTANT,  # Using constant for locals
                        line=var_line,
                        column=var_match.start(),
                        scope="local",
                        visibility="private",
                    )
                )

        return locals_vars

    def extract_imports(self, content: str) -> List[Import]:
        """Extract import-like references from Terraform."""
        imports = []

        # Extract module sources
        module_source_pattern = r'module\s+"[^"]+"\s*\{[^}]*source\s*=\s*"([^"]+)"'
        for match in re.finditer(module_source_pattern, content, re.DOTALL):
            line_num = content[: match.start()].count("\n") + 1
            source = match.group(1)

            imports.append(
                Import(
                    module=source,
                    line=line_num,
                    is_relative=not source.startswith(
                        ("http://", "https://", "git::", "registry.terraform.io")
                    ),
                    alias=None,
                )
            )

        # Extract terraform required_providers
        provider_pattern = r'required_providers\s*\{[^}]*([a-zA-Z_][a-zA-Z0 - 9_-]*)\s*=\s*\{[^}]*source\s*=\s*"([^"]+)"'  # noqa: E501
        for match in re.finditer(provider_pattern, content, re.DOTALL):
            line_num = content[: match.start()].count("\n") + 1
            provider_name = match.group(1)
            source = match.group(2)

            imports.append(
                Import(
                    module=source, line=line_num, is_relative=False, alias=provider_name
                )
            )

        # Extract file references
        file_patterns = [
            r'file\s*\(\s*"([^"]+)"\s*\)',
            r'templatefile\s*\(\s*"([^"]+)"',
            r'jsonencode\s*\(\s*file\s*\(\s*"([^"]+)"\s*\)\s*\)',
        ]

        for pattern in file_patterns:
            for match in re.finditer(pattern, content):
                line_num = content[: match.start()].count("\n") + 1
                file_path = match.group(1)

                imports.append(
                    Import(
                        module=file_path,
                        line=line_num,
                        is_relative=not file_path.startswith("/"),
                        alias=None,
                    )
                )

        return imports

    def calculate_metrics(self, content: str, symbols: List[Symbol]) -> CodeMetrics:
        """Calculate Terraform-specific metrics."""
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
            elif stripped.startswith("#") or stripped.startswith("//"):
                comment_lines += 1
            elif stripped.startswith("/*"):
                comment_lines += 1
                if not stripped.endswith("*/"):
                    in_block_comment = True
            else:
                code_lines += 1

        # Calculate complexity based on conditionals and iterations
        complexity = 1  # Base complexity
        complexity_keywords = [
            r"\bfor\b",
            r"\bif\b",
            r"\bcount\b",
            r"\bfor_each\b",
            r"\bdynamic\b",
            r"\btry\b",
            r"\bcan\b",
        ]

        for keyword in complexity_keywords:
            complexity += len(re.findall(keyword, content))

        # Calculate nesting depth
        max_depth = 0
        current_depth = 0

        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            # Count opening and closing braces
            open_braces = line.count("{")
            close_braces = line.count("}")

            current_depth += open_braces - close_braces
            max_depth = max(max_depth, current_depth)
            current_depth = max(0, current_depth)

        # Count different symbol types
        resource_count = len([s for s in symbols if s.scope == "resource"])
        module_count = len([s for s in symbols if s.scope == "module"])

        return CodeMetrics(
            lines_of_code=code_lines,
            cyclomatic_complexity=complexity,
            cognitive_complexity=complexity,
            maintainability_index=max(0, 171 - 5.2 * complexity - 0.23 * code_lines),
            function_count=module_count,  # Modules are like functions
            class_count=resource_count,  # Resources are like classes
            max_nesting_depth=max_depth,
            comment_ratio=comment_lines / max(len(lines), 1),
        )

    def parse_file(self, file_path: Path, content: str) -> AnalysisResult:
        """Parse a Terraform file and extract symbols, imports, and metrics."""
        symbols = self.extract_symbols(content)
        imports = self.extract_imports(content)
        metrics = self.calculate_metrics(content, symbols)

        # Resolve dependencies from imports
        dependencies = self.resolve_dependencies(imports, file_path.parent)

        return AnalysisResult(
            file_path=file_path,
            language="terraform",
            symbols=symbols,
            imports=imports,
            metrics=metrics,
            dependencies=dependencies,
            syntax_errors=[],
        )


# Register the analyzer
if __name__ != "__main__":
    tf_analyzer = TerraformAnalyzer()
    language_registry.register(tf_analyzer)
