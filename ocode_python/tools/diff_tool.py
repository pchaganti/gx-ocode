"""
Diff tool for comparing files.
"""

import difflib
from pathlib import Path
from typing import Any

from .base import Tool, ToolDefinition, ToolParameter, ToolResult


class DiffTool(Tool):
    """Tool for comparing two files and showing differences."""

    @property
    def definition(self) -> ToolDefinition:
        """Define the diff tool specification.

        Returns:
            ToolDefinition with parameters for comparing files including
            file paths, diff format options, and context settings.
        """
        return ToolDefinition(
            name="diff",
            description="Compare two files and show differences",
            parameters=[
                ToolParameter(
                    name="file1",
                    type="string",
                    description="Path to the first file",
                    required=True,
                ),
                ToolParameter(
                    name="file2",
                    type="string",
                    description="Path to the second file",
                    required=True,
                ),
                ToolParameter(
                    name="unified",
                    type="boolean",
                    description="Use unified diff format (default: true)",
                    required=False,
                    default=True,
                ),
                ToolParameter(
                    name="context_lines",
                    type="number",
                    description="Number of context lines to show (default: 3)",
                    required=False,
                    default=3,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute diff command."""
        try:
            file1 = kwargs.get("file1", "")
            file2 = kwargs.get("file2", "")
            unified = kwargs.get("unified", True)
            context_lines = kwargs.get("context_lines", 3)

            if not file1 or not file2:
                return ToolResult(
                    success=False,
                    output="",
                    error="Both file1 and file2 paths are required",
                )
            path1 = Path(file1)
            path2 = Path(file2)

            # Check if files exist
            if not path1.exists():
                return ToolResult(
                    success=False, output="", error=f"File not found: {file1}"
                )

            if not path2.exists():
                return ToolResult(
                    success=False, output="", error=f"File not found: {file2}"
                )

            # Read file contents
            try:
                with open(path1, "r", encoding="utf-8", errors="replace") as f:
                    lines1 = f.readlines()
            except Exception as e:
                return ToolResult(
                    success=False, output="", error=f"Error reading {file1}: {str(e)}"
                )

            try:
                with open(path2, "r", encoding="utf-8", errors="replace") as f:
                    lines2 = f.readlines()
            except Exception as e:
                return ToolResult(
                    success=False, output="", error=f"Error reading {file2}: {str(e)}"
                )

            # Generate diff
            if unified:
                diff_lines = list(
                    difflib.unified_diff(
                        lines1, lines2, fromfile=file1, tofile=file2, n=context_lines
                    )
                )
            else:
                diff_lines = list(
                    difflib.context_diff(
                        lines1, lines2, fromfile=file1, tofile=file2, n=context_lines
                    )
                )

            if not diff_lines:
                return ToolResult(
                    success=True,
                    output="Files are identical",
                    metadata={"identical": True, "file1": file1, "file2": file2},
                )

            # Join diff lines and remove extra newlines
            output = "".join(diff_lines).rstrip("\n")

            return ToolResult(
                success=True,
                output=output,
                metadata={
                    "identical": False,
                    "file1": file1,
                    "file2": file2,
                    "diff_lines": len(diff_lines),
                },
            )

        except Exception as e:
            return ToolResult(
                success=False, output="", error=f"Error comparing files: {str(e)}"
            )
