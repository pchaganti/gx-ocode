"""
Markdown language analyzer.
"""

import re
from pathlib import Path
from typing import List, Set

from .base import (
    AnalysisResult,
    Import,
    LanguageAnalyzer,
    Symbol,
    SymbolType,
    language_registry,
)


class MarkdownAnalyzer(LanguageAnalyzer):
    """Markdown language analyzer."""

    @property
    def file_extensions(self) -> List[str]:
        """Return list of file extensions this analyzer handles."""
        return [".md", ".markdown", ".mdown", ".mkd"]

    @property
    def comment_patterns(self) -> List[str]:
        """Return list of comment patterns for this language."""
        return ["<!--", "<!---"]

    def extract_symbols(self, content: str) -> List[Symbol]:
        """Extract symbols from Markdown content."""
        symbols = []

        # Extract headers
        symbols.extend(self._extract_headers(content))

        # Extract code blocks with language tags
        symbols.extend(self._extract_code_blocks(content))

        # Extract links
        symbols.extend(self._extract_links(content))

        return symbols

    def _extract_headers(self, content: str) -> List[Symbol]:
        """Extract header definitions."""
        headers = []

        for line_num, line in enumerate(content.split("\n"), 1):
            # ATX-style headers (# Header)
            atx_match = re.match(r"^(#{1,6})\s+(.+)", line.strip())
            if atx_match:
                level = len(atx_match.group(1))
                title = atx_match.group(2).strip()
                headers.append(
                    Symbol(
                        name=title,
                        type=SymbolType.NAMESPACE,  # Using namespace for headers
                        line=line_num,
                        column=0,
                        scope=f"h{level}",
                        visibility="public",
                    )
                )

            # Setext-style headers (underlined)
            elif line_num < len(content.split("\n")):
                next_line = (
                    content.split("\n")[line_num]
                    if line_num < len(content.split("\n"))
                    else ""
                )
                if re.match(r"^=+\s*$", next_line.strip()):
                    # H1
                    headers.append(
                        Symbol(
                            name=line.strip(),
                            type=SymbolType.NAMESPACE,
                            line=line_num,
                            column=0,
                            scope="h1",
                            visibility="public",
                        )
                    )
                elif re.match(r"^-+\s*$", next_line.strip()):
                    # H2
                    headers.append(
                        Symbol(
                            name=line.strip(),
                            type=SymbolType.NAMESPACE,
                            line=line_num,
                            column=0,
                            scope="h2",
                            visibility="public",
                        )
                    )

        return headers

    def _extract_code_blocks(self, content: str) -> List[Symbol]:
        """Extract code blocks with language specifications."""
        code_blocks = []

        # Fenced code blocks (```)
        fenced_pattern = r"```(\w+)?\n(.*?)\n```"
        for match in re.finditer(fenced_pattern, content, re.DOTALL):
            line_num = content[: match.start()].count("\n") + 1
            language = match.group(1) or "text"

            code_blocks.append(
                Symbol(
                    name=f"code_block_{language}",
                    type=SymbolType.MODULE,  # Using module for code blocks
                    line=line_num,
                    column=match.start() - content.rfind("\n", 0, match.start()),
                    scope=language,
                    visibility="public",
                )
            )

        # Indented code blocks (4+ spaces)
        lines = content.split("\n")
        in_code_block = False
        code_block_start = 0

        for line_num, line in enumerate(lines, 1):
            is_code_line = line.startswith("    ") or line.startswith("\t")

            if is_code_line and not in_code_block:
                in_code_block = True
                code_block_start = line_num
            elif not is_code_line and in_code_block:
                in_code_block = False
                code_blocks.append(
                    Symbol(
                        name="code_block_indented",
                        type=SymbolType.MODULE,
                        line=code_block_start,
                        column=0,
                        scope="indented",
                        visibility="public",
                    )
                )

        return code_blocks

    def _extract_links(self, content: str) -> List[Symbol]:
        """Extract link definitions."""
        links = []

        # Inline links [text](url)
        inline_pattern = r"\[([^\]]+)\]\(([^)]+)\)"
        for match in re.finditer(inline_pattern, content):
            line_num = content[: match.start()].count("\n") + 1
            link_text = match.group(1)

            links.append(
                Symbol(
                    name=link_text,
                    type=SymbolType.VARIABLE,  # Using variable for links
                    line=line_num,
                    column=match.start() - content.rfind("\n", 0, match.start()),
                    visibility="public",
                )
            )

        # Reference links [text][ref]
        ref_pattern = r"\[([^\]]+)\]\[([^\]]+)\]"
        for match in re.finditer(ref_pattern, content):
            line_num = content[: match.start()].count("\n") + 1
            link_text = match.group(1)

            links.append(
                Symbol(
                    name=link_text,
                    type=SymbolType.VARIABLE,
                    line=line_num,
                    column=match.start() - content.rfind("\n", 0, match.start()),
                    visibility="public",
                )
            )

        return links

    def extract_imports(self, content: str) -> List[Import]:
        """Extract import-like references from Markdown."""
        imports = []

        # Extract image references
        img_pattern = r"!\[([^\]]*)\]\(([^)]+)\)"
        for match in re.finditer(img_pattern, content):
            line_num = content[: match.start()].count("\n") + 1
            img_src = match.group(2)

            # Only include relative paths (local files)
            if not img_src.startswith(("http://", "https://", "ftp://", "mailto:")):
                imports.append(
                    Import(
                        module=img_src,
                        line=line_num,
                        is_relative=not img_src.startswith("/"),
                        alias=match.group(1) if match.group(1) else None,
                    )
                )

        # Extract link references to local files
        link_pattern = r"\[([^\]]+)\]\(([^)]+)\)"
        for match in re.finditer(link_pattern, content):
            line_num = content[: match.start()].count("\n") + 1
            link_url = match.group(2)

            # Only include relative paths that look like files
            if not link_url.startswith(
                ("http://", "https://", "ftp://", "mailto:", "#")
            ) and ("." in link_url or link_url.endswith("/")):
                imports.append(
                    Import(
                        module=link_url,
                        line=line_num,
                        is_relative=not link_url.startswith("/"),
                        alias=match.group(1),
                    )
                )

        return imports

    def parse_file(self, file_path: Path, content: str) -> AnalysisResult:
        """Parse a Markdown file and extract symbols, imports, and metrics."""
        symbols = self.extract_symbols(content)
        imports = self.extract_imports(content)
        metrics = self.calculate_metrics(content, symbols)

        # No dependencies for Markdown files typically
        dependencies: Set[str] = set()

        return AnalysisResult(
            file_path=file_path,
            language="markdown",
            symbols=symbols,
            imports=imports,
            metrics=metrics,
            dependencies=dependencies,
            syntax_errors=[],
        )


# Register the analyzer
if __name__ != "__main__":
    md_analyzer = MarkdownAnalyzer()
    language_registry.register(md_analyzer)
