"""
Which tool for finding executable programs in PATH.
"""

import os
import shutil
from pathlib import Path

from .base import Tool, ToolDefinition, ToolParameter, ToolResult


class WhichTool(Tool):
    """Tool for finding executable programs in PATH."""

    @property
    def definition(self) -> ToolDefinition:
        """Define the which tool specification.

        Returns:
            ToolDefinition with parameters for locating executable programs
            in the system PATH.
        """
        return ToolDefinition(
            name="which",
            description="Locate executable programs in PATH",
            parameters=[
                ToolParameter(
                    name="command",
                    type="string",
                    description="Command name to locate",
                    required=True,
                ),
                ToolParameter(
                    name="all",
                    type="boolean",
                    description="Show all matching executables in PATH (-a flag)",
                    required=False,
                    default=False,
                ),
            ],
        )

    async def execute(self, **kwargs) -> ToolResult:
        """Execute which command."""
        try:
            command = kwargs.get("command", "")
            all = kwargs.get("all", False)

            if all:
                # Find all instances of the command in PATH
                paths = []
                path_env = os.environ.get("PATH", "")

                for path_dir_str in path_env.split(os.pathsep):
                    if not path_dir_str:
                        continue

                    path_dir = Path(path_dir_str)
                    if not path_dir.exists() or not path_dir.is_dir():
                        continue

                    # Check for the command in this directory
                    cmd_path = path_dir / command
                    if cmd_path.exists() and cmd_path.is_file():
                        # Check if it's executable
                        if os.access(cmd_path, os.X_OK):
                            paths.append(str(cmd_path))

                    # On Windows, also check with common executable extensions
                    if os.name == "nt":
                        for ext in [".exe", ".bat", ".cmd", ".com"]:
                            cmd_path_ext = path_dir / f"{command}{ext}"
                            if cmd_path_ext.exists() and cmd_path_ext.is_file():
                                if os.access(cmd_path_ext, os.X_OK):
                                    paths.append(str(cmd_path_ext))

                if paths:
                    output = "\n".join(paths)
                    return ToolResult(
                        success=True,
                        output=output,
                        metadata={
                            "command": command,
                            "found_paths": paths,
                            "count": len(paths),
                        },
                    )
                else:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Command not found: {command}",
                        metadata={"command": command, "found": False},
                    )

            else:
                # Find first instance using shutil.which
                cmd_path = shutil.which(command)

                if cmd_path:
                    return ToolResult(
                        success=True,
                        output=cmd_path,
                        metadata={"command": command, "path": cmd_path, "found": True},
                    )
                else:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Command not found: {command}",
                        metadata={"command": command, "found": False},
                    )

        except Exception as e:
            return ToolResult(
                success=False, output="", error=f"Error locating command: {str(e)}"
            )
