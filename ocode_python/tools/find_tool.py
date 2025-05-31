"""
Find tool for searching files and directories.
"""

import asyncio
import fnmatch
import os
from pathlib import Path
from typing import List, Optional, Tuple

from ..utils import path_validator
from ..utils.timeout_handler import async_timeout
from .base import (
    ErrorHandler,
    ErrorType,
    Tool,
    ToolDefinition,
    ToolParameter,
    ToolResult,
)


class FindTool(Tool):
    """Tool for finding files and directories by various criteria."""

    @property
    def definition(self) -> ToolDefinition:
        """Define the find tool specification.

        Returns:
            ToolDefinition with parameters for finding files and directories
            by name patterns, type, size, modification time, and content.
        """
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
        file_type: Optional[str] = None,
        maxdepth: Optional[int] = None,
        size: Optional[str] = None,
        extension: Optional[str] = None,
        **kwargs,
    ) -> ToolResult:
        """Execute find command."""
        try:
            # Map old 'type' parameter name to new 'file_type' for backwards compat
            if "type" in kwargs:
                file_type = kwargs.get("type")
            # Use file_type parameter
            # Validate path
            is_valid, error_msg, normalized_path = path_validator.validate_path(
                path, check_exists=True
            )
            if not is_valid or normalized_path is None:
                return ErrorHandler.create_error_result(
                    f"Invalid path: {error_msg}", ErrorType.VALIDATION_ERROR
                )

            # At this point normalized_path is guaranteed to be non-None
            assert normalized_path is not None  # Type safety for MyPy
            search_path = normalized_path

            # Limit search depth to prevent excessive resource usage
            if maxdepth is None or maxdepth > 20:
                maxdepth = 20  # Reasonable default to prevent runaway searches

            results: List[str] = []
            processed_count = 0
            max_results = 10000  # Limit results to prevent memory issues

            # Walk through directory tree with timeout protection
            try:
                async with async_timeout(
                    60
                ):  # 60 second timeout for directory traversal
                    for root, dirs, files in os.walk(str(search_path)):
                        # Prevent excessive processing
                        processed_count += len(dirs) + len(files)
                        if processed_count > 100000:  # Limit total items processed
                            return ErrorHandler.create_error_result(
                                "Search stopped: too many items to process (> 100k)",
                                ErrorType.RESOURCE_ERROR,
                            )

                        current_depth = len(Path(root).relative_to(search_path).parts)

                        # Check maxdepth
                        if maxdepth is not None and current_depth > maxdepth:
                            dirs[:] = []  # Don't recurse deeper
                            continue

                        # Process directories
                        if file_type != "f":  # Not files-only
                            for dir_name in dirs:
                                if len(results) >= max_results:
                                    break
                                dir_path = Path(root) / dir_name

                                # Apply filters
                                if file_type == "d" or file_type is None:
                                    if name and not fnmatch.fnmatch(dir_name, name):
                                        continue
                                    if extension and not dir_name.endswith(extension):
                                        continue

                                    results.append(str(dir_path))

                        # Process files
                        if file_type != "d":  # Not directories-only
                            for file_name in files:
                                if len(results) >= max_results:
                                    break
                                file_path = Path(root) / file_name

                                # Apply filters
                                if file_type == "f" or file_type is None:
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

                        if len(results) >= max_results:
                            break
            except asyncio.TimeoutError:
                return ErrorHandler.create_error_result(
                    "Search timed out - directory tree too large or complex",
                    ErrorType.TIMEOUT_ERROR,
                )

            # Sort results for consistent output
            results.sort()

            if not results:
                return ErrorHandler.create_success_result(
                    "No files found matching criteria",
                    metadata={"matches": 0, "search_path": str(search_path)},
                )

            output = "\n".join(results)

            # Add warning if results were truncated
            if len(results) >= max_results:
                output += f"\n\n[WARNING: Results truncated at {max_results} items]"

            return ErrorHandler.create_success_result(
                output,
                metadata={
                    "matches": len(results),
                    "search_path": str(search_path),
                    "truncated": len(results) >= max_results,
                    "filters": {
                        "name": name,
                        "type": file_type,
                        "maxdepth": maxdepth,
                        "size": size,
                        "extension": extension,
                    },
                },
            )

        except Exception as e:
            return ErrorHandler.handle_exception(e, "find_tool")
