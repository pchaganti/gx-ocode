"""
Enhanced directory listing tool with metadata and filtering capabilities.
"""

import os
import stat
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import Tool, ToolDefinition, ToolParameter, ToolResult


class LsTool(Tool):
    """Enhanced directory listing tool with metadata and filtering."""

    @property
    def definition(self) -> ToolDefinition:
        """Define the ls tool specification.

        Returns:
            ToolDefinition with parameters for listing directory contents
            with options for filtering, sorting, and detailed information.
        """
        return ToolDefinition(
            name="ls",
            description="List directory contents with detailed information and filtering",  # noqa: E501
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path to list (file or directory)",
                    required=False,
                    default=".",
                ),
                ToolParameter(
                    name="all",
                    type="boolean",
                    description="Show hidden files and directories (starting with .)",
                    required=False,
                    default=False,
                ),
                ToolParameter(
                    name="long_format",
                    type="boolean",
                    description="Use long format showing permissions, size, dates, etc.",  # noqa: E501
                    required=False,
                    default=True,
                ),
                ToolParameter(
                    name="recursive",
                    type="boolean",
                    description="List contents recursively",
                    required=False,
                    default=False,
                ),
                ToolParameter(
                    name="sort_by",
                    type="string",
                    description="Sort by: 'name', 'size', 'modified', 'created', 'extension'",  # noqa: E501
                    required=False,
                    default="name",
                ),
                ToolParameter(
                    name="reverse_sort",
                    type="boolean",
                    description="Reverse sort order",
                    required=False,
                    default=False,
                ),
                ToolParameter(
                    name="file_types",
                    type="array",
                    description="Filter by file types: ['file', 'dir', 'link', 'executable']",  # noqa: E501
                    required=False,
                    default=[],
                ),
                ToolParameter(
                    name="extensions",
                    type="array",
                    description="Filter by file extensions (e.g., ['.py', '.js'])",
                    required=False,
                    default=[],
                ),
                ToolParameter(
                    name="size_filter",
                    type="object",
                    description="Size filter: {'min': '1KB', 'max': '10MB'}",
                    required=False,
                ),
                ToolParameter(
                    name="max_depth",
                    type="number",
                    description="Maximum recursion depth (0 = unlimited)",
                    required=False,
                    default=0,
                ),
                ToolParameter(
                    name="show_tree",
                    type="boolean",
                    description="Show as tree structure (only when recursive=True)",
                    required=False,
                    default=False,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute directory listing."""
        try:
            # Extract parameters from kwargs
            path = kwargs.get("path", ".")
            all = kwargs.get("all", False)
            long_format = kwargs.get("long_format", True)
            recursive = kwargs.get("recursive", False)
            sort_by = kwargs.get("sort_by", "name")
            reverse_sort = kwargs.get("reverse_sort", False)
            file_types = kwargs.get("file_types", [])
            extensions = kwargs.get("extensions", [])
            size_filter = kwargs.get("size_filter")
            max_depth = kwargs.get("max_depth", 0)
            show_tree = kwargs.get("show_tree", False)

            target_path = Path(path).resolve()

            if not target_path.exists():
                return ToolResult(
                    success=False, output="", error=f"Path does not exist: {path}"
                )

            file_types = file_types or []
            extensions = extensions or []

            if target_path.is_file():
                # Show single file info
                file_info = self._get_file_info(target_path, long_format)
                return ToolResult(
                    success=True,
                    output=self._format_single_file(file_info, long_format),
                    metadata={"files": [file_info], "total_count": 1},
                )

            # List directory contents
            if recursive:
                files_info = self._list_recursive(
                    target_path,
                    all,
                    long_format,
                    max_depth,
                    file_types,
                    extensions,
                    size_filter,
                )
            else:
                files_info = self._list_directory(
                    target_path, all, long_format, file_types, extensions, size_filter
                )

            # Sort files
            files_info = self._sort_files(files_info, sort_by, reverse_sort)

            # Format output
            if show_tree and recursive:
                output = self._format_tree(files_info, target_path)
            else:
                output = self._format_listing(files_info, long_format, target_path)

            return ToolResult(
                success=True,
                output=output,
                metadata={
                    "files": files_info,
                    "total_count": len(files_info),
                    "path": str(target_path),
                    "filters_applied": {
                        "file_types": file_types,
                        "extensions": extensions,
                        "size_filter": size_filter,
                    },
                },
            )

        except Exception as e:
            return ToolResult(
                success=False, output="", error=f"Directory listing failed: {str(e)}"
            )

    def _list_directory(
        self,
        dir_path: Path,
        show_hidden: bool,
        long_format: bool,
        file_types: List[str],
        extensions: List[str],
        size_filter: Optional[Dict[str, str]],
    ) -> List[Dict[str, Any]]:
        """List contents of a single directory."""
        files_info = []

        try:
            for item in dir_path.iterdir():
                # Skip hidden files if not requested
                if not show_hidden and item.name.startswith("."):
                    continue

                file_info = self._get_file_info(item, long_format)

                # Apply filters
                if self._passes_filters(file_info, file_types, extensions, size_filter):
                    files_info.append(file_info)

        except PermissionError:
            pass  # Skip directories we can't read

        return files_info

    def _list_recursive(
        self,
        base_path: Path,
        show_hidden: bool,
        long_format: bool,
        max_depth: int,
        file_types: List[str],
        extensions: List[str],
        size_filter: Optional[Dict[str, str]],
    ) -> List[Dict[str, Any]]:
        """List contents recursively."""
        files_info = []

        def _walk_directory(current_path: Path, current_depth: int):
            if max_depth > 0 and current_depth > max_depth:
                return

            try:
                for item in current_path.iterdir():
                    # Skip hidden files if not requested
                    if not show_hidden and item.name.startswith("."):
                        continue

                    file_info = self._get_file_info(item, long_format)
                    file_info["depth"] = current_depth

                    # Apply filters
                    if self._passes_filters(
                        file_info, file_types, extensions, size_filter
                    ):
                        files_info.append(file_info)

                    # Recurse into directories
                    if item.is_dir():
                        _walk_directory(item, current_depth + 1)

            except PermissionError:
                pass  # Skip directories we can't read

        _walk_directory(base_path, 0)
        return files_info

    def _get_file_info(self, file_path: Path, long_format: bool) -> Dict[str, Any]:
        """Get detailed information about a file or directory."""
        try:
            file_stat = file_path.stat()

            info = {
                "name": file_path.name,
                "path": str(file_path),
                "type": self._get_file_type(file_path, file_stat),
                "size": file_stat.st_size if file_path.is_file() else 0,
                "modified": datetime.fromtimestamp(file_stat.st_mtime).isoformat(),
                "created": datetime.fromtimestamp(file_stat.st_ctime).isoformat(),
            }

            if long_format:
                info.update(
                    {
                        "permissions": stat.filemode(file_stat.st_mode),
                        "owner_readable": bool(file_stat.st_mode & stat.S_IRUSR),
                        "owner_writable": bool(file_stat.st_mode & stat.S_IWUSR),
                        "owner_executable": bool(file_stat.st_mode & stat.S_IXUSR),
                        "modified_timestamp": file_stat.st_mtime,
                        "size_formatted": self._format_size(file_stat.st_size),
                        "extension": (
                            file_path.suffix.lower() if file_path.is_file() else ""
                        ),
                        "is_hidden": file_path.name.startswith("."),
                        "is_symlink": file_path.is_symlink(),
                    }
                )

                if file_path.is_symlink():
                    try:
                        import os

                        info["symlink_target"] = str(os.readlink(file_path))
                    except OSError:
                        info["symlink_target"] = "<broken link>"

            return info

        except OSError as e:
            return {
                "name": file_path.name,
                "path": str(file_path),
                "type": "unknown",
                "size": 0,
                "error": str(e),
            }

    def _get_file_type(self, file_path: Path, file_stat: os.stat_result) -> str:
        """Determine the type of file."""
        if file_path.is_symlink():
            return "link"
        elif file_path.is_dir():
            return "dir"
        elif file_path.is_file():
            if file_stat.st_mode & stat.S_IXUSR:
                return "executable"
            else:
                return "file"
        else:
            return "special"

    def _passes_filters(
        self,
        file_info: Dict[str, Any],
        file_types: List[str],
        extensions: List[str],
        size_filter: Optional[Dict[str, str]],
    ) -> bool:
        """Check if file passes all filters."""
        # File type filter
        if file_types and file_info["type"] not in file_types:
            return False

        # Extension filter
        if extensions:
            file_ext = file_info.get("extension", "")
            if not any(file_ext == ext.lower() for ext in extensions):
                return False

        # Size filter
        if size_filter and file_info["type"] == "file":
            file_size = file_info["size"]

            if "min" in size_filter:
                min_size = self._parse_size(size_filter["min"])
                if file_size < min_size:
                    return False

            if "max" in size_filter:
                max_size = self._parse_size(size_filter["max"])
                if file_size > max_size:
                    return False

        return True

    def _sort_files(
        self, files_info: List[Dict[str, Any]], sort_by: str, reverse: bool
    ) -> List[Dict[str, Any]]:
        """Sort files by specified criteria."""
        sort_key_map = {
            "name": lambda f: f["name"].lower(),
            "size": lambda f: f["size"],
            "modified": lambda f: f.get("modified_timestamp", 0),
            "created": lambda f: f.get("created", ""),
            "extension": lambda f: f.get("extension", ""),
        }

        if sort_by in sort_key_map:
            files_info.sort(key=sort_key_map[sort_by], reverse=reverse)

        return files_info

    def _format_single_file(self, file_info: Dict[str, Any], long_format: bool) -> str:
        """Format single file information."""
        if long_format:
            perms = file_info.get("permissions", "?????????")
            size = file_info.get("size_formatted", "")
            modified = file_info.get("modified", "")[:19]
            name = str(file_info["name"])

            if file_info["type"] == "dir":
                name = f"📁 {name}/"
            elif file_info["type"] == "link":
                target = file_info.get("symlink_target", "")
                name = f"🔗 {name} -> {target}"
            elif file_info["type"] == "executable":
                name = f"⚡ {name}"
            else:
                name = f"📄 {name}"

            return f"{perms} {size:>8} {modified} {name}"
        else:
            name = str(file_info["name"])
            if file_info["type"] == "dir":
                name = f"{name}/"
            return name

    def _format_listing(
        self, files_info: List[Dict[str, Any]], long_format: bool, base_path: Path
    ) -> str:
        """Format file listing output."""
        if not files_info:
            return f"No files found in {base_path}"

        lines = []

        if long_format:
            # Calculate column widths
            max_size_width = max(len(f.get("size_formatted", "")) for f in files_info)

            # Header
            lines.append(
                f"{'Permissions':<11} {'Size':>{max_size_width}} {'Modified':<19} {'Name'}"  # noqa: E501
            )
            lines.append("-" * (11 + max_size_width + 19 + 20))

            # File entries
            for file_info in files_info:
                perms = file_info.get("permissions", "?????????")
                size = file_info.get("size_formatted", "")
                modified = file_info.get("modified", "")[:19]  # Truncate seconds
                name = file_info["name"]

                # Add type indicator
                if file_info["type"] == "dir":
                    name = f"📁 {name}/"
                elif file_info["type"] == "link":
                    target = file_info.get("symlink_target", "")
                    name = f"🔗 {name} -> {target}"
                elif file_info["type"] == "executable":
                    name = f"⚡ {name}"
                else:
                    name = f"📄 {name}"

                lines.append(
                    f"{perms:<11} {size:>{max_size_width}} {modified:<19} {name}"
                )
        else:
            # Simple format
            for file_info in files_info:
                name = file_info["name"]
                if file_info["type"] == "dir":
                    name = f"{name}/"
                lines.append(name)

        # Summary
        total_size = sum(f["size"] for f in files_info if f["type"] == "file")
        dir_count = sum(1 for f in files_info if f["type"] == "dir")
        file_count = sum(1 for f in files_info if f["type"] == "file")

        lines.append("")
        lines.append(
            f"Total: {file_count} files, {dir_count} directories, {self._format_size(total_size)}"  # noqa: E501
        )

        return "\\n".join(lines)

    def _format_tree(self, files_info: List[Dict[str, Any]], base_path: Path) -> str:
        """Format files as a tree structure."""
        lines = [f"📁 {base_path.name}/"]

        # Group files by directory
        tree_dict: Dict[str, Any] = {}
        for file_info in files_info:
            file_path = Path(file_info["path"])
            relative_path = file_path.relative_to(base_path)

            # Build nested dict structure
            current = tree_dict
            for part in relative_path.parts[:-1]:  # All but the last part
                if part not in current:
                    current[part] = {}
                current = current[part]

            # Add file to final directory
            current[relative_path.name] = file_info

        # Render tree
        def _render_tree(tree_dict: Dict, prefix: str = "", is_last: bool = True):
            items = list(tree_dict.items())
            for i, (name, content) in enumerate(items):
                is_last_item = i == len(items) - 1
                current_prefix = "└── " if is_last_item else "├── "

                if isinstance(content, dict) and not content.get("type"):
                    # Directory node
                    lines.append(f"{prefix}{current_prefix}📁 {name}/")
                    next_prefix = prefix + ("    " if is_last_item else "│   ")
                    _render_tree(content, next_prefix, is_last_item)
                else:
                    # File node
                    file_type = content.get("type", "file")
                    icon = {
                        "dir": "📁",
                        "file": "📄",
                        "executable": "⚡",
                        "link": "🔗",
                    }.get(file_type, "📄")
                    lines.append(f"{prefix}{current_prefix}{icon} {name}")

        _render_tree(tree_dict)
        return "\\n".join(lines)

    def _format_size(self, size: int) -> str:
        """Format file size in human-readable format."""
        size_float = float(size)
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_float < 1024.0:
                return (
                    f"{size_float:.1f}{unit}"
                    if size_float != int(size_float)
                    else f"{int(size_float)}{unit}"
                )
            size_float = size_float / 1024.0
        return f"{size_float:.1f}PB"

    def _parse_size(self, size_str: str) -> int:
        """Parse size string like '1KB', '10MB' to bytes."""
        size_str = size_str.upper().strip()

        multipliers = {
            "B": 1,
            "KB": 1024,
            "MB": 1024 * 1024,
            "GB": 1024 * 1024 * 1024,
            "TB": 1024 * 1024 * 1024 * 1024,
        }

        for suffix, multiplier in multipliers.items():
            if size_str.endswith(suffix):
                number_part = size_str[: -len(suffix)]
                return int(float(number_part) * multiplier)

        # Default to bytes if no suffix
        return int(float(size_str))
