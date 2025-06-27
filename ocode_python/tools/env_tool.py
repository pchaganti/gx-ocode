"""
Environment variable management tool.
"""

import json
import os
import re
from pathlib import Path
from typing import Any, Optional

from dotenv import dotenv_values, load_dotenv

from .base import Tool, ToolDefinition, ToolParameter, ToolResult


class EnvironmentTool(Tool):
    """Tool for managing environment variables."""

    @property
    def definition(self) -> ToolDefinition:
        """Define the environment tool specification.

        Returns:
            ToolDefinition with parameters for managing environment variables
            including get, set, unset, list, load from .env files, and save operations.
        """
        return ToolDefinition(
            name="env",
            description="Get, set, and manage environment variables",
            category="System Operations",
            parameters=[
                ToolParameter(
                    name="action",
                    type="string",
                    description="Action: get, set, unset, list, load, save",
                    required=True,
                ),
                ToolParameter(
                    name="name",
                    type="string",
                    description="Environment variable name",
                    required=False,
                ),
                ToolParameter(
                    name="value",
                    type="string",
                    description="Value to set",
                    required=False,
                ),
                ToolParameter(
                    name="file",
                    type="string",
                    description="Path to .env file (default: .env)",
                    required=False,
                    default=".env",
                ),
                ToolParameter(
                    name="pattern",
                    type="string",
                    description="Regex pattern to filter variables (for list action)",
                    required=False,
                ),
                ToolParameter(
                    name="export",
                    type="boolean",
                    description="Export variables to current process (for load action)",
                    required=False,
                    default=False,
                ),
                ToolParameter(
                    name="format",
                    type="string",
                    description="Output format: text, json, export (default: text)",
                    required=False,
                    default="text",
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute environment variable operations."""
        action = kwargs.get("action", "").lower()
        name = kwargs.get("name")
        value = kwargs.get("value")
        file_path = kwargs.get("file", ".env")
        pattern = kwargs.get("pattern")
        export = kwargs.get("export", False)
        output_format = kwargs.get("format", "text").lower()

        if not action:
            return ToolResult(
                success=False, output="", error="Action parameter is required"
            )

        valid_actions = ["get", "set", "unset", "list", "load", "save"]
        if action not in valid_actions:
            return ToolResult(
                success=False,
                output="",
                error=f"Invalid action. Must be one of: {', '.join(valid_actions)}",
            )

        try:
            if action == "get":
                if not name:
                    return ToolResult(
                        success=False,
                        output="",
                        error="Name parameter is required for 'get' action",
                    )
                return await self._action_get(name, output_format)

            elif action == "set":
                if not name:
                    return ToolResult(
                        success=False,
                        output="",
                        error="Name parameter is required for 'set' action",
                    )
                if value is None:
                    return ToolResult(
                        success=False,
                        output="",
                        error="Value parameter is required for 'set' action",
                    )
                return await self._action_set(name, value)

            elif action == "unset":
                if not name:
                    return ToolResult(
                        success=False,
                        output="",
                        error="Name parameter is required for 'unset' action",
                    )
                return await self._action_unset(name)

            elif action == "list":
                return await self._action_list(pattern, output_format)

            elif action == "load":
                return await self._action_load(file_path, export, output_format)

            elif action == "save":
                return await self._action_save(file_path, pattern)

            # This should never happen due to validation above, but included for completeness  # noqa: E501
            return ToolResult(
                success=False,
                output="",
                error=f"Unknown action: {action}",
            )

        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Error executing environment operation: {str(e)}",
            )

    async def _action_get(self, name: str, output_format: str) -> ToolResult:
        """Get an environment variable value."""
        # Validate variable name
        if not self._is_valid_var_name(name):
            return ToolResult(
                success=False, output="", error=f"Invalid variable name: {name}"
            )

        value = os.environ.get(name)

        if value is None:
            return ToolResult(
                success=True,
                output=f"Environment variable '{name}' is not set",
                metadata={"name": name, "exists": False},
            )

        # Format output
        if output_format == "json":
            output = json.dumps({name: value}, indent=2)
        elif output_format == "export":
            output = f'export {name}="{value}"'
        else:  # text
            output = value

        return ToolResult(
            success=True,
            output=output,
            metadata={"name": name, "exists": True, "length": len(value)},
        )

    async def _action_set(self, name: str, value: str) -> ToolResult:
        """Set an environment variable."""
        # Validate variable name
        if not self._is_valid_var_name(name):
            return ToolResult(
                success=False, output="", error=f"Invalid variable name: {name}"
            )

        # Check if it already exists
        old_value = os.environ.get(name)

        # Set the variable
        os.environ[name] = value

        return ToolResult(
            success=True,
            output=f"Set {name}={value}",
            metadata={
                "name": name,
                "value": value,
                "previous_value": old_value,
                "updated": old_value is not None,
            },
        )

    async def _action_unset(self, name: str) -> ToolResult:
        """Unset an environment variable."""
        # Validate variable name
        if not self._is_valid_var_name(name):
            return ToolResult(
                success=False, output="", error=f"Invalid variable name: {name}"
            )

        if name in os.environ:
            old_value = os.environ[name]
            del os.environ[name]
            return ToolResult(
                success=True,
                output=f"Unset {name}",
                metadata={"name": name, "previous_value": old_value},
            )
        else:
            return ToolResult(
                success=True,
                output=f"Environment variable '{name}' was not set",
                metadata={"name": name, "was_set": False},
            )

    async def _action_list(
        self, pattern: Optional[str], output_format: str
    ) -> ToolResult:
        """List environment variables."""
        env_vars = dict(os.environ)

        # Filter by pattern if provided
        if pattern:
            try:
                regex = re.compile(pattern)
                env_vars = {k: v for k, v in env_vars.items() if regex.search(k)}
            except re.error as e:
                return ToolResult(
                    success=False, output="", error=f"Invalid regex pattern: {e}"
                )

        if not env_vars:
            return ToolResult(
                success=True,
                output="No environment variables found",
                metadata={"count": 0, "pattern": pattern},
            )

        # Sort by key
        sorted_vars = sorted(env_vars.items())

        # Format output
        if output_format == "json":
            output = json.dumps(dict(sorted_vars), indent=2)
        elif output_format == "export":
            lines = []
            for key, value in sorted_vars:
                # Escape quotes in value
                escaped_value = value.replace('"', '\\"')
                lines.append(f'export {key}="{escaped_value}"')
            output = "\n".join(lines)
        else:  # text
            lines = []
            for key, value in sorted_vars:
                # Truncate long values
                if len(value) > 100:
                    display_value = value[:97] + "..."
                else:
                    display_value = value
                lines.append(f"{key}={display_value}")
            output = "\n".join(lines)

        return ToolResult(
            success=True,
            output=output,
            metadata={"count": len(env_vars), "pattern": pattern},
        )

    async def _action_load(
        self, file_path: str, export: bool, output_format: str
    ) -> ToolResult:
        """Load environment variables from a .env file."""
        env_file = Path(file_path)

        if not env_file.exists():
            return ToolResult(
                success=False, output="", error=f"File not found: {file_path}"
            )

        if not env_file.is_file():
            return ToolResult(
                success=False, output="", error=f"Not a file: {file_path}"
            )

        # Load variables
        if export:
            # Export to current process
            loaded = load_dotenv(env_file, override=True)
            if not loaded:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Failed to load .env file: {file_path}",
                )

            # Get the loaded values
            env_values = dotenv_values(env_file)
        else:
            # Just read without exporting
            env_values = dotenv_values(env_file)

        if not env_values:
            return ToolResult(
                success=True,
                output=f"No variables found in {file_path}",
                metadata={"file": str(file_path), "count": 0, "exported": export},
            )

        # Format output
        if output_format == "json":
            output = json.dumps(env_values, indent=2)
        else:  # text
            lines = [f"Loaded {len(env_values)} variables from {file_path}:"]
            if export:
                lines.append("(Exported to current process)")
            lines.append("")
            for key, value in sorted(env_values.items()):
                lines.append(f"{key}={value}")
            output = "\n".join(lines)

        return ToolResult(
            success=True,
            output=output,
            metadata={
                "file": str(file_path),
                "count": len(env_values),
                "exported": export,
                "variables": list(env_values.keys()),
            },
        )

    async def _action_save(self, file_path: str, pattern: Optional[str]) -> ToolResult:
        """Save environment variables to a .env file."""
        env_file = Path(file_path)

        # Create parent directory if needed
        env_file.parent.mkdir(parents=True, exist_ok=True)

        # Get variables to save
        env_vars = dict(os.environ)

        # Filter by pattern if provided
        if pattern:
            try:
                regex = re.compile(pattern)
                env_vars = {k: v for k, v in env_vars.items() if regex.search(k)}
            except re.error as e:
                return ToolResult(
                    success=False, output="", error=f"Invalid regex pattern: {e}"
                )

        if not env_vars:
            return ToolResult(
                success=True,
                output="No variables to save",
                metadata={"count": 0, "pattern": pattern},
            )

        # Write to file
        lines = []
        for key, value in sorted(env_vars.items()):
            # Escape special characters
            if '"' in value or "\n" in value or "#" in value:
                # Use double quotes and escape
                escaped_value = (
                    value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
                )
                lines.append(f'{key}="{escaped_value}"')
            elif " " in value:
                # Quote if contains spaces
                lines.append(f'{key}="{value}"')
            else:
                lines.append(f"{key}={value}")

        try:
            with open(env_file, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
                f.write("\n")  # End with newline

            return ToolResult(
                success=True,
                output=f"Saved {len(env_vars)} variables to {file_path}",
                metadata={
                    "file": str(file_path),
                    "count": len(env_vars),
                    "pattern": pattern,
                    "variables": list(env_vars.keys()),
                },
            )
        except Exception as e:
            return ToolResult(
                success=False, output="", error=f"Failed to write file: {e}"
            )

    def _is_valid_var_name(self, name: str) -> bool:
        """Check if a variable name is valid."""
        # Must start with letter or underscore, followed by letters, numbers, or underscores  # noqa: E501
        return bool(re.match(r"^[A-Za-z_][A-Za-z0 - 9_]*$", name))
