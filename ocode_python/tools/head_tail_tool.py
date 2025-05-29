"""
Head and tail tools for viewing file contents.
"""

from pathlib import Path

from .base import Tool, ToolDefinition, ToolParameter, ToolResult


class HeadTool(Tool):
    """Tool for viewing the first N lines of a file."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="head",
            description="Display the first lines of a file",
            parameters=[
                ToolParameter(
                    name="file_path",
                    type="string",
                    description="Path to the file to read",
                    required=True,
                ),
                ToolParameter(
                    name="lines",
                    type="number",
                    description="Number of lines to display (default: 10)",
                    required=False,
                    default=10,
                ),
            ],
        )

    async def execute(self, **kwargs) -> ToolResult:
        """Execute head command."""
        file_path = kwargs.get("file_path")
        lines = kwargs.get("lines", 10)

        if not file_path:
            return ToolResult(success=False, output="", error="file_path is required")
        try:
            path = Path(file_path)

            if not path.exists():
                return ToolResult(
                    success=False, output="", error=f"File not found: {file_path}"
                )

            if not path.is_file():
                return ToolResult(
                    success=False, output="", error=f"Not a file: {file_path}"
                )

            # Read first N lines
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                file_lines = []
                for i, line in enumerate(f):
                    if i >= lines:
                        break
                    file_lines.append(line.rstrip("\n\r"))

            output = "\n".join(file_lines)
            return ToolResult(
                success=True,
                output=output,
                metadata={"file": str(path), "lines_shown": len(file_lines)},
            )

        except Exception as e:
            return ToolResult(
                success=False, output="", error=f"Error reading file: {str(e)}"
            )


class TailTool(Tool):
    """Tool for viewing the last N lines of a file."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="tail",
            description="Display the last lines of a file",
            parameters=[
                ToolParameter(
                    name="file_path",
                    type="string",
                    description="Path to the file to read",
                    required=True,
                ),
                ToolParameter(
                    name="lines",
                    type="number",
                    description="Number of lines to display (default: 10)",
                    required=False,
                    default=10,
                ),
            ],
        )

    async def execute(self, **kwargs) -> ToolResult:
        """Execute tail command."""
        file_path = kwargs.get("file_path")
        lines = kwargs.get("lines", 10)

        if not file_path:
            return ToolResult(success=False, output="", error="file_path is required")
        try:
            path = Path(file_path)

            if not path.exists():
                return ToolResult(
                    success=False, output="", error=f"File not found: {file_path}"
                )

            if not path.is_file():
                return ToolResult(
                    success=False, output="", error=f"Not a file: {file_path}"
                )

            # Read all lines and get last N
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                all_lines = f.readlines()

            # Get last N lines
            last_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines

            # Remove trailing newlines for consistent output
            output_lines = [line.rstrip("\n\r") for line in last_lines]
            output = "\n".join(output_lines)

            return ToolResult(
                success=True,
                output=output,
                metadata={
                    "file": str(path),
                    "lines_shown": len(output_lines),
                    "total_lines": len(all_lines),
                },
            )

        except Exception as e:
            return ToolResult(
                success=False, output="", error=f"Error reading file: {str(e)}"
            )
