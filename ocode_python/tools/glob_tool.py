"""
File pattern matching and discovery tool using glob patterns.
"""

import fnmatch
import glob
from pathlib import Path
from typing import Any

from .base import Tool, ToolDefinition, ToolParameter, ToolResult


class GlobTool(Tool):
    """Tool for file pattern matching and discovery using glob patterns."""

    @property
    def definition(self) -> ToolDefinition:
        """Define the glob tool specification.

        Returns:
            ToolDefinition with parameters for file pattern matching using
            glob syntax including wildcards, recursive patterns, and filtering.
        """
        return ToolDefinition(
            name="glob",
            description="Find files and directories using glob patterns",
            parameters=[
                ToolParameter(
                    name="pattern",
                    type="string",
                    description="Glob pattern to match files (e.g., '*.py', '**/*.ts', 'src/**/*.{js,ts}')",  # noqa: E501
                    required=True,
                ),
                ToolParameter(
                    name="path",
                    type="string",
                    description="Base path to search from (default: current directory)",  # noqa: E501
                    required=False,
                    default=".",
                ),
                ToolParameter(
                    name="recursive",
                    type="boolean",
                    description="Enable recursive search (use ** in pattern for recursive)",  # noqa: E501
                    required=False,
                    default=True,
                ),
                ToolParameter(
                    name="include_dirs",
                    type="boolean",
                    description="Include directories in results",
                    required=False,
                    default=False,
                ),
                ToolParameter(
                    name="include_hidden",
                    type="boolean",
                    description="Include hidden files and directories",
                    required=False,
                    default=False,
                ),
                ToolParameter(
                    name="max_results",
                    type="number",
                    description="Maximum number of results to return",
                    required=False,
                    default=100,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute glob pattern matching."""
        try:
            pattern = kwargs.get("pattern")
            if not pattern:
                return ToolResult(
                    success=False, output="", error="Pattern is required"
                )  # noqa: E501

            path = kwargs.get("path", ".")
            recursive = kwargs.get("recursive", True)
            include_dirs = kwargs.get("include_dirs", False)
            include_hidden = kwargs.get("include_hidden", False)
            max_results = kwargs.get("max_results", 100)

            base_path = Path(path).resolve()

            if not base_path.exists():
                return ToolResult(
                    success=False, output="", error=f"Base path does not exist: {path}"
                )

            # Build glob pattern
            if recursive and "**" not in pattern:
                # Make pattern recursive if not already
                glob_pattern = str(base_path / "**" / pattern)
            else:
                glob_pattern = str(base_path / pattern)

            # Find matching files
            matches = glob.glob(glob_pattern, recursive=recursive)

            # Filter results
            filtered_matches = []
            for match in matches:
                match_path = Path(match)

                # Skip hidden files if not included
                if not include_hidden and any(
                    part.startswith(".") for part in match_path.parts
                ):
                    continue

                # Filter directories if not included
                if match_path.is_dir() and not include_dirs:
                    continue

                filtered_matches.append(match)

                # Stop if we hit max results
                if len(filtered_matches) >= max_results:
                    break

            # Sort results for consistent output
            filtered_matches.sort()

            # Format output
            if not filtered_matches:
                output = f"No files found matching pattern: {pattern}"
            else:
                # Create detailed output with file info
                output_lines = [
                    f"Found {len(filtered_matches)} matches for pattern '{pattern}':"
                ]

                for match in filtered_matches:
                    match_path = Path(match)
                    relative_path = match_path.relative_to(base_path)

                    if match_path.is_dir():
                        output_lines.append(f"  📁 {relative_path}/")
                    else:
                        # Get file size
                        try:
                            size = match_path.stat().st_size
                            if size > 1024 * 1024:
                                size_str = f"{size / (1024 * 1024):.1f}MB"
                            elif size > 1024:
                                size_str = f"{size / 1024:.1f}KB"
                            else:
                                size_str = f"{size}B"

                            output_lines.append(f"  📄 {relative_path} ({size_str})")
                        except OSError:
                            output_lines.append(f"  📄 {relative_path}")

                if len(matches) > max_results:
                    output_lines.append(
                        f"  ... and {len(matches) - max_results} more (use max_results to see more)"  # noqa: E501
                    )

                output = "\n".join(output_lines)

            return ToolResult(
                success=True,
                output=output,
                metadata={
                    "pattern": pattern,
                    "base_path": str(base_path),
                    "matches_found": len(filtered_matches),
                    "total_matches": len(matches),
                    "files": [
                        str(Path(m).relative_to(base_path)) for m in filtered_matches
                    ],
                },
            )

        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Glob pattern matching failed: {str(e)}",
            )

    def _matches_pattern(self, file_path: Path, pattern: str) -> bool:
        """Check if a file path matches a glob pattern."""
        try:
            return fnmatch.fnmatch(str(file_path), pattern)
        except Exception:
            return False


class AdvancedGlobTool(GlobTool):
    """Enhanced glob tool with additional filtering capabilities."""

    @property
    def definition(self) -> ToolDefinition:
        base_def = super().definition
        base_def.parameters.extend(
            [
                ToolParameter(
                    name="exclude_patterns",
                    type="array",
                    description="Patterns to exclude from results (e.g., ['*.pyc', '__pycache__/*'])",  # noqa: E501
                    required=False,
                    default=[],
                ),
                ToolParameter(
                    name="file_extensions",
                    type="array",
                    description="Filter by file extensions (e.g., ['.py', '.js', '.ts'])",  # noqa: E501
                    required=False,
                    default=[],
                ),
                ToolParameter(
                    name="modified_since",
                    type="string",
                    description="ISO timestamp - only files modified since this time",
                    required=False,
                ),
                ToolParameter(
                    name="size_range",
                    type="object",
                    description="File size range filter (e.g., {'min': '1KB', 'max': '10MB'})",  # noqa: E501
                    required=False,
                ),
            ]
        )
        return base_def

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute advanced glob pattern matching with additional filters."""

        # Extract parameters
        pattern = kwargs.get("pattern")
        path = kwargs.get("path", ".")
        recursive = kwargs.get("recursive", True)
        include_dirs = kwargs.get("include_dirs", False)
        include_hidden = kwargs.get("include_hidden", False)
        max_results = kwargs.get("max_results", 100)
        exclude_patterns = kwargs.get("exclude_patterns", [])
        file_extensions = kwargs.get("file_extensions", [])
        modified_since = kwargs.get("modified_since")
        size_range = kwargs.get("size_range")

        # First run basic glob
        result = await super().execute(
            **{
                "pattern": pattern,
                "path": path,
                "recursive": recursive,
                "include_dirs": include_dirs,
                "include_hidden": include_hidden,
                "max_results": max_results * 2,
            }
        )

        if not result.success or not result.metadata:
            return result

        # Apply additional filters
        base_path = Path(path).resolve()
        filtered_files = []

        for file_rel_path in result.metadata.get("files", []):
            file_path = base_path / file_rel_path

            # Check exclude patterns
            if exclude_patterns:
                if any(
                    fnmatch.fnmatch(str(file_path), exclude_pat)
                    for exclude_pat in exclude_patterns
                ):
                    continue

            # Check file extensions
            if file_extensions:
                if file_path.suffix.lower() not in [
                    ext.lower() for ext in file_extensions
                ]:
                    continue

            # Check modification time
            if modified_since:
                try:
                    from datetime import datetime

                    mod_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                    since_time = datetime.fromisoformat(
                        modified_since.replace("Z", "+00:00")
                    )
                    if mod_time < since_time:
                        continue
                except (ValueError, OSError):
                    continue

            # Check size range
            if size_range:
                try:
                    file_size = file_path.stat().st_size
                    if "min" in size_range:
                        min_size = self._parse_size(size_range["min"])
                        if file_size < min_size:
                            continue
                    if "max" in size_range:
                        max_size = self._parse_size(size_range["max"])
                        if file_size > max_size:
                            continue
                except (ValueError, OSError):
                    continue

            filtered_files.append(file_rel_path)

            if len(filtered_files) >= max_results:
                break

        # Update result with filtered files
        if filtered_files:
            output_lines = [f"Found {len(filtered_files)} matches (after filtering):"]
            for file_path in filtered_files:
                full_path = base_path / file_path
                if full_path.is_dir():
                    output_lines.append(f"  📁 {file_path}/")
                else:
                    output_lines.append(f"  📄 {file_path}")

            result.output = "\n".join(output_lines)
            result.metadata["files"] = filtered_files
            result.metadata["matches_found"] = len(filtered_files)
        else:
            result.output = "No files found matching the specified filters"
            result.metadata["files"] = []
            result.metadata["matches_found"] = 0

        return result

    def _parse_size(self, size_str: str) -> int:
        """Parse size string like '1KB', '10MB' to bytes."""
        size_str = size_str.upper().strip()

        multipliers = {"B": 1, "KB": 1024, "MB": 1024 * 1024, "GB": 1024 * 1024 * 1024}

        for suffix, multiplier in multipliers.items():
            if size_str.endswith(suffix):
                number_part = size_str[: -len(suffix)]
                return int(float(number_part) * multiplier)

        # Default to bytes if no suffix
        return int(size_str)
