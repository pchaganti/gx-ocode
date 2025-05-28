"""
Word count tool for counting lines, words, and characters.
"""

from pathlib import Path
from typing import List, Optional

from .base import Tool, ToolDefinition, ToolParameter, ToolResult


class WcTool(Tool):
    """Tool for counting lines, words, and characters in files."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="wc",
            description="Count lines, words, and characters in files",
            parameters=[
                ToolParameter(
                    name="file_path",
                    type="string",
                    description="Path to the file to analyze",
                    required=True
                ),
                ToolParameter(
                    name="lines_only",
                    type="boolean",
                    description="Count lines only (-l flag)",
                    required=False,
                    default=False
                ),
                ToolParameter(
                    name="words_only",
                    type="boolean",
                    description="Count words only (-w flag)",
                    required=False,
                    default=False
                ),
                ToolParameter(
                    name="chars_only",
                    type="boolean",
                    description="Count characters only (-c flag)",
                    required=False,
                    default=False
                )
            ]
        )

    async def execute(self, file_path: str, lines_only: bool = False, words_only: bool = False, chars_only: bool = False, **kwargs) -> ToolResult:
        """Execute wc command."""
        try:
            path = Path(file_path)
            
            if not path.exists():
                return ToolResult(
                    success=False,
                    output="",
                    error=f"File not found: {file_path}"
                )
            
            if not path.is_file():
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Not a file: {file_path}"
                )
            
            # Read file content
            try:
                with open(path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
            except Exception as e:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Error reading file: {str(e)}"
                )
            
            # Count metrics
            lines = content.count('\n')
            # Add 1 if file doesn't end with newline but has content
            if content and not content.endswith('\n'):
                lines += 1
            
            words = len(content.split())
            chars = len(content)
            
            # Format output based on flags
            output_parts = []
            
            if lines_only:
                output_parts.append(str(lines))
            elif words_only:
                output_parts.append(str(words))
            elif chars_only:
                output_parts.append(str(chars))
            else:
                # Default: show all counts
                output_parts = [str(lines), str(words), str(chars)]
            
            output_parts.append(str(path))
            output = " ".join(output_parts)
            
            return ToolResult(
                success=True,
                output=output,
                metadata={
                    "file": str(path),
                    "lines": lines,
                    "words": words,
                    "characters": chars
                }
            )
            
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Error counting file contents: {str(e)}"
            )