"""
Text processing tools for sort, uniq, and other text operations.
"""

from pathlib import Path
from typing import Dict, Optional

from .base import Tool, ToolDefinition, ToolParameter, ToolResult


class SortTool(Tool):
    """Tool for sorting lines in files or text."""

    @property
    def definition(self) -> ToolDefinition:
        """Define the sort tool specification.

        Returns:
            ToolDefinition with parameters for sorting text or file contents
            with options for reverse order, numeric sort, and custom keys.
        """
        return ToolDefinition(
            name="sort",
            description="Sort lines in a file or text",
            parameters=[
                ToolParameter(
                    name="file_path",
                    type="string",
                    description="Path to file to sort (optional, can sort text directly)",  # noqa: E501
                    required=False,
                ),
                ToolParameter(
                    name="text",
                    type="string",
                    description="Text to sort (if no file_path provided)",
                    required=False,
                ),
                ToolParameter(
                    name="reverse",
                    type="boolean",
                    description="Sort in reverse order (-r flag)",
                    required=False,
                    default=False,
                ),
                ToolParameter(
                    name="numeric",
                    type="boolean",
                    description="Sort numerically (-n flag)",
                    required=False,
                    default=False,
                ),
                ToolParameter(
                    name="unique",
                    type="boolean",
                    description="Output only unique lines (-u flag)",
                    required=False,
                    default=False,
                ),
            ],
        )

    async def execute(
        self,
        file_path: Optional[str] = None,
        text: Optional[str] = None,
        reverse: bool = False,
        numeric: bool = False,
        unique: bool = False,
        **kwargs,
    ) -> ToolResult:
        """Execute sort command."""
        try:
            # Get input lines
            if file_path:
                path = Path(file_path)
                if not path.exists():
                    return ToolResult(
                        success=False, output="", error=f"File not found: {file_path}"
                    )

                if not path.is_file():
                    return ToolResult(
                        success=False, output="", error=f"Not a file: {file_path}"
                    )

                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    lines = f.read().splitlines()

            elif text:
                lines = text.splitlines()

            else:
                return ToolResult(
                    success=False,
                    output="",
                    error="Must provide either file_path or text to sort",
                )

            # Sort lines
            if numeric:

                def sort_key(line):
                    """Extract numeric value from line for sorting.

                    Args:
                        line: Text line to extract number from.

                    Returns:
                        Float value for sorting, inf for non-numeric lines.
                    """
                    # Try to extract numbers from the beginning of lines
                    try:
                        # Find first sequence of digits (with optional decimal)
                        import re

                        match = re.match(r"^[+-]?(\d+\.?\d*)", line.strip())
                        if match:
                            return float(match.group())
                        return float("inf")  # Non-numeric lines go to end
                    except (ValueError, AttributeError):
                        return float("inf")

                sorted_lines = sorted(lines, key=sort_key, reverse=reverse)
            else:
                sorted_lines = sorted(lines, reverse=reverse)

            # Remove duplicates if unique flag is set
            if unique:
                seen = set()
                unique_lines = []
                for line in sorted_lines:
                    if line not in seen:
                        seen.add(line)
                        unique_lines.append(line)
                sorted_lines = unique_lines

            output = "\n".join(sorted_lines)

            return ToolResult(
                success=True,
                output=output,
                metadata={
                    "input_lines": len(lines),
                    "output_lines": len(sorted_lines),
                    "sorted": True,
                    "reverse": reverse,
                    "numeric": numeric,
                    "unique": unique,
                },
            )

        except Exception as e:
            return ToolResult(
                success=False, output="", error=f"Error sorting: {str(e)}"
            )


class UniqTool(Tool):
    """Tool for removing duplicate lines."""

    @property
    def definition(self) -> ToolDefinition:
        """Define the uniq tool specification.

        Returns:
            ToolDefinition with parameters for removing duplicate lines
            with options for counting occurrences and showing duplicates.
        """
        return ToolDefinition(
            name="uniq",
            description="Remove duplicate lines from sorted input",
            parameters=[
                ToolParameter(
                    name="file_path",
                    type="string",
                    description="Path to file to process (optional, can process text directly)",  # noqa: E501
                    required=False,
                ),
                ToolParameter(
                    name="text",
                    type="string",
                    description="Text to process (if no file_path provided)",
                    required=False,
                ),
                ToolParameter(
                    name="count",
                    type="boolean",
                    description="Show count of occurrences (-c flag)",
                    required=False,
                    default=False,
                ),
                ToolParameter(
                    name="duplicates_only",
                    type="boolean",
                    description="Show only duplicate lines (-d flag)",
                    required=False,
                    default=False,
                ),
            ],
        )

    async def execute(
        self,
        file_path: Optional[str] = None,
        text: Optional[str] = None,
        count: bool = False,
        duplicates_only: bool = False,
        **kwargs,
    ) -> ToolResult:
        """Execute uniq command."""
        try:
            # Get input lines
            if file_path:
                path = Path(file_path)
                if not path.exists():
                    return ToolResult(
                        success=False, output="", error=f"File not found: {file_path}"
                    )

                if not path.is_file():
                    return ToolResult(
                        success=False, output="", error=f"Not a file: {file_path}"
                    )

                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    lines = f.read().splitlines()

            elif text:
                lines = text.splitlines()

            else:
                return ToolResult(
                    success=False,
                    output="",
                    error="Must provide either file_path or text to process",
                )

            # Process lines for uniqueness
            line_counts: Dict[str, int] = {}
            for line in lines:
                line_counts[line] = line_counts.get(line, 0) + 1

            # Generate output based on flags
            output_lines = []

            for line in lines:
                line_count = line_counts[line]

                # Skip if we've already processed this line
                if line_counts[line] == 0:
                    continue

                # Apply filters
                if duplicates_only and line_count == 1:
                    line_counts[line] = 0  # Mark as processed
                    continue

                # Format output
                if count:
                    output_lines.append(f"{line_count:>7} {line}")
                else:
                    output_lines.append(line)

                # Mark as processed
                line_counts[line] = 0

            output = "\n".join(output_lines)

            total_unique = len([c for c in line_counts.values() if c > 0]) + len(
                output_lines
            )
            duplicates = sum(1 for line, cnt in line_counts.items() if cnt > 1)

            return ToolResult(
                success=True,
                output=output,
                metadata={
                    "input_lines": len(lines),
                    "output_lines": len(output_lines),
                    "unique_lines": total_unique,
                    "duplicates_found": duplicates,
                    "count": count,
                    "duplicates_only": duplicates_only,
                },
            )

        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Error processing unique lines: {str(e)}",
            )
