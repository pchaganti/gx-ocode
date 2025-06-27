"""
File operations tools for copy, move, and remove operations.
"""

import shutil
from pathlib import Path
from typing import Any

from .base import ResourceLock, Tool, ToolDefinition, ToolParameter, ToolResult


class CopyTool(Tool):
    """Tool for copying files and directories."""

    @property
    def definition(self) -> ToolDefinition:
        """Define the cp (copy) tool specification.

        Returns:
            ToolDefinition with parameters for copying files and directories
            with options for recursive copy, preservation, and overwrite control.
        """
        return ToolDefinition(
            name="cp",
            description="Copy files or directories",
            resource_locks=[ResourceLock.FILESYSTEM_WRITE],
            parameters=[
                ToolParameter(
                    name="source",
                    type="string",
                    description="Source file or directory path",
                    required=True,
                ),
                ToolParameter(
                    name="destination",
                    type="string",
                    description="Destination file or directory path",
                    required=True,
                ),
                ToolParameter(
                    name="recursive",
                    type="boolean",
                    description="Copy directories recursively (-r flag)",
                    required=False,
                    default=False,
                ),
                ToolParameter(
                    name="preserve",
                    type="boolean",
                    description="Preserve file metadata (timestamps, permissions)",
                    required=False,
                    default=True,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute copy command."""
        try:
            source = kwargs.get("source", "")
            destination = kwargs.get("destination", "")
            recursive = kwargs.get("recursive", False)
            preserve = kwargs.get("preserve", True)

            if not source or not destination:
                return ToolResult(
                    success=False,
                    output="",
                    error="Source and destination paths are required",
                )

            src_path = Path(source)
            dst_path = Path(destination)

            if not src_path.exists():
                return ToolResult(
                    success=False, output="", error=f"Source not found: {source}"
                )

            # If source is a directory but recursive is False
            if src_path.is_dir() and not recursive:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Cannot copy directory without recursive flag: {source}",
                )

            # Create parent directories if they don't exist
            dst_path.parent.mkdir(parents=True, exist_ok=True)

            if src_path.is_file():
                if preserve:
                    shutil.copy2(src_path, dst_path)
                else:
                    shutil.copy(src_path, dst_path)

                return ToolResult(
                    success=True,
                    output=f"Copied file: {source} -> {destination}",
                    metadata={
                        "source": source,
                        "destination": str(dst_path),
                        "type": "file",
                    },
                )

            elif src_path.is_dir():
                if dst_path.exists() and dst_path.is_file():
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Cannot copy directory to existing file: {destination}",
                    )

                if preserve:
                    shutil.copytree(src_path, dst_path, dirs_exist_ok=True)
                else:
                    shutil.copytree(
                        src_path,
                        dst_path,
                        dirs_exist_ok=True,
                        copy_function=shutil.copy,
                    )

                return ToolResult(
                    success=True,
                    output=f"Copied directory: {source} -> {destination}",
                    metadata={
                        "source": source,
                        "destination": str(dst_path),
                        "type": "directory",
                    },
                )

            else:
                return ToolResult(
                    success=False, output="", error=f"Unknown file type: {source}"
                )

        except Exception as e:
            return ToolResult(
                success=False, output="", error=f"Error copying: {str(e)}"
            )


class MoveTool(Tool):
    """Tool for moving/renaming files and directories."""

    @property
    def definition(self) -> ToolDefinition:
        """Define the mv (move) tool specification.

        Returns:
            ToolDefinition with parameters for moving or renaming files
            and directories with force and interactive options.
        """
        return ToolDefinition(
            name="mv",
            description="Move or rename files and directories",
            resource_locks=[ResourceLock.FILESYSTEM_WRITE],
            parameters=[
                ToolParameter(
                    name="source",
                    type="string",
                    description="Source file or directory path",
                    required=True,
                ),
                ToolParameter(
                    name="destination",
                    type="string",
                    description="Destination file or directory path",
                    required=True,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute move command."""
        try:
            source = kwargs.get("source", "")
            destination = kwargs.get("destination", "")

            if not source or not destination:
                return ToolResult(
                    success=False,
                    output="",
                    error="Source and destination paths are required",
                )
            src_path = Path(source)
            dst_path = Path(destination)

            if not src_path.exists():
                return ToolResult(
                    success=False, output="", error=f"Source not found: {source}"
                )

            # Create parent directories if they don't exist
            dst_path.parent.mkdir(parents=True, exist_ok=True)

            # Check if destination exists and is a directory
            if dst_path.exists() and dst_path.is_dir():
                # Move source into the directory
                dst_path = dst_path / src_path.name

            shutil.move(str(src_path), str(dst_path))

            return ToolResult(
                success=True,
                output=f"Moved: {source} -> {dst_path}",
                metadata={"source": source, "destination": str(dst_path)},
            )

        except Exception as e:
            return ToolResult(
                success=False, output="", error=f"Error moving: {str(e)}"
            )  # noqa: E501


class RemoveTool(Tool):
    """Tool for removing files and directories with safety checks."""

    @property
    def definition(self) -> ToolDefinition:
        """Define the rm (remove) tool specification.

        Returns:
            ToolDefinition with parameters for safely removing files and
            directories with options for recursive deletion and force mode.
        """
        return ToolDefinition(
            name="rm",
            description="Remove files and directories (with safety checks)",
            resource_locks=[ResourceLock.FILESYSTEM_WRITE],
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path to file or directory to remove",
                    required=True,
                ),
                ToolParameter(
                    name="recursive",
                    type="boolean",
                    description="Remove directories recursively (-r flag)",
                    required=False,
                    default=False,
                ),
                ToolParameter(
                    name="force",
                    type="boolean",
                    description="Force removal without prompts (-f flag)",
                    required=False,
                    default=False,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute remove command with safety checks."""
        try:
            path = kwargs.get("path", "")
            recursive = kwargs.get("recursive", False)
            force = kwargs.get("force", False)

            if not path:
                return ToolResult(success=False, output="", error="Path is required")

            target_path = Path(path)

            if not target_path.exists():
                return ToolResult(
                    success=False, output="", error=f"Path not found: {path}"
                )

            # Safety checks - prevent removing critical system paths
            critical_paths = [
                Path("/"),
                Path("/bin"),
                Path("/etc"),
                Path("/usr"),
                Path("/var"),
                Path("/sys"),
                Path("/proc"),
                Path.home(),
                Path.cwd(),
            ]

            abs_target = target_path.resolve()
            for critical in critical_paths:
                try:
                    critical_abs = critical.resolve()
                    if (
                        abs_target == critical_abs or critical_abs in abs_target.parents
                    ):  # noqa: E501
                        return ToolResult(
                            success=False,
                            output="",
                            error=f"Safety check: Refusing to remove critical path: {path}",  # noqa: E501
                        )
                except (OSError, RuntimeError):
                    # Ignore errors resolving critical paths
                    continue

            # Don't allow removing current working directory
            if abs_target == Path.cwd().resolve():
                return ToolResult(
                    success=False,
                    output="",
                    error="Safety check: Cannot remove current working directory",
                )

            if target_path.is_file():
                target_path.unlink()
                return ToolResult(
                    success=True,
                    output=f"Removed file: {path}",
                    metadata={"path": path, "type": "file"},
                )

            elif target_path.is_dir():
                if not recursive:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Cannot remove directory without recursive flag: {path}",  # noqa: E501
                    )

                # Additional safety check for directories
                if not force:
                    # Check if directory has many files (potential safety issue)
                    file_count = sum(1 for _ in target_path.rglob("*") if _.is_file())
                    if file_count > 100:
                        return ToolResult(
                            success=False,
                            output="",
                            error=f"Safety check: Directory contains {file_count} files. Use force=true to override.",  # noqa: E501
                        )

                shutil.rmtree(target_path)
                return ToolResult(
                    success=True,
                    output=f"Removed directory: {path}",
                    metadata={"path": path, "type": "directory"},
                )

            else:
                return ToolResult(
                    success=False, output="", error=f"Unknown file type: {path}"
                )

        except Exception as e:
            return ToolResult(
                success=False, output="", error=f"Error removing: {str(e)}"
            )
