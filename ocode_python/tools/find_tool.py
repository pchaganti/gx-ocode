"""
Find tool for searching files and directories.
"""

import fnmatch
import os
from pathlib import Path
from typing import Optional, Tuple

from .base import Tool, ToolDefinition, ToolParameter, ToolResult


class FindTool(Tool):
    """Tool for finding files and directories by various criteria."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="find",
            description="Find files and directories by name, size, type, etc.",
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path to search in (default: current directory)",
                    required=False,
                    default=".",
                ),
                ToolParameter(
                    name="name",
                    type="string",
                    description="File name pattern (supports wildcards)",
                    required=False,
                ),
                ToolParameter(
                    name="type",
                    type="string",
                    description="File type: 'f' for files, 'd' for directories",
                    required=False,
                ),
                ToolParameter(
                    name="maxdepth",
                    type="number",
                    description="Maximum directory depth to search",
                    required=False,
                ),
                ToolParameter(
                    name="size",
                    type="string",
                    description="File size filter (e.g., '+1M', '-100k')",
                    required=False,
                ),
                ToolParameter(
                    name="extension",
                    type="string",
                    description="File extension to search for (e.g., '.py', '.txt')",
                    required=False,
                ),
            ],
        )

    def _parse_size(self, size_str: str) -> Tuple[Optional[str], int]:
        """Parse size string like '+1M', '-100k' into (operator, bytes)."""
        if not size_str:
            return None, 0

        size_str = size_str.strip()
        if not size_str:
            return None, 0

        # Determine operator
        operator = "="
        if size_str.startswith(("+", "-")):
            operator = size_str[0]
            size_str = size_str[1:]

        # Parse size and unit
        multipliers = {
            "b": 1,
            "B": 1,
            "k": 1024,
            "K": 1024,
            "m": 1024**2,
            "M": 1024**2,
            "g": 1024**3,
            "G": 1024**3,
        }

        if size_str[-1] in multipliers:
            unit = size_str[-1]
            number = size_str[:-1]
        else:
            unit = "b"
            number = size_str

        try:
            size_bytes = int(number) * multipliers[unit]
            return operator, size_bytes
        except (ValueError, KeyError):
            return None, 0

    def _matches_size(self, file_size: int, size_filter: str) -> bool:
        """Check if file size matches the filter."""
        operator, target_size = self._parse_size(size_filter)
        if operator is None:
            return True

        if operator == "+":
            return bool(file_size > target_size)
        elif operator == "-":
            return bool(file_size < target_size)
        else:  # '='
            return bool(file_size == target_size)

    async def execute(
        self,
        path: str = ".",
        name: Optional[str] = None,
        type: Optional[str] = None,
        maxdepth: Optional[int] = None,
        size: Optional[str] = None,
        extension: Optional[str] = None,
        **kwargs,
    ) -> ToolResult:
        """Execute find command."""
        try:
            search_path = Path(path)

            if not search_path.exists():
                return ToolResult(
                    success=False, output="", error=f"Path not found: {path}"
                )

            results = []

            # Walk through directory tree
            for root, dirs, files in os.walk(search_path):
                current_depth = len(Path(root).relative_to(search_path).parts)

                # Check maxdepth
                if maxdepth is not None and current_depth > maxdepth:
                    dirs[:] = []  # Don't recurse deeper
                    continue

                # Process directories
                if type != "f":  # Not files-only
                    for dir_name in dirs:
                        dir_path = Path(root) / dir_name

                        # Apply filters
                        if type == "d" or type is None:
                            if name and not fnmatch.fnmatch(dir_name, name):
                                continue
                            if extension and not dir_name.endswith(extension):
                                continue

                            results.append(str(dir_path))

                # Process files
                if type != "d":  # Not directories-only
                    for file_name in files:
                        file_path = Path(root) / file_name

                        # Apply filters
                        if type == "f" or type is None:
                            if name and not fnmatch.fnmatch(file_name, name):
                                continue
                            if extension and not file_name.endswith(extension):
                                continue

                            # Size filter
                            if size:
                                try:
                                    file_size = file_path.stat().st_size
                                    if not self._matches_size(file_size, size):
                                        continue
                                except OSError:
                                    continue

                            results.append(str(file_path))

            # Sort results for consistent output
            results.sort()

            if not results:
                return ToolResult(
                    success=True,
                    output="No files found matching criteria",
                    metadata={"matches": 0, "search_path": str(search_path)},
                )

            output = "\n".join(results)

            return ToolResult(
                success=True,
                output=output,
                metadata={
                    "matches": len(results),
                    "search_path": str(search_path),
                    "filters": {
                        "name": name,
                        "type": type,
                        "maxdepth": maxdepth,
                        "size": size,
                        "extension": extension,
                    },
                },
            )

        except Exception as e:
            return ToolResult(
                success=False, output="", error=f"Error searching files: {str(e)}"
            )
