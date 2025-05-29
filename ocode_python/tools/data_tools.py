"""
Tools for JSON and YAML data processing.
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import yaml
from jsonpath_ng import parse as jsonpath_parse
from jsonpath_ng.exceptions import JsonPathParserError

from .base import Tool, ToolDefinition, ToolParameter, ToolResult


class JsonYamlTool(Tool):
    """Tool for parsing, querying, and manipulating JSON/YAML data."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="json_yaml",
            description="Parse, query, and manipulate JSON/YAML data files or strings",
            category="Data Processing",
            parameters=[
                ToolParameter(
                    name="action",
                    type="string",
                    description="Action to perform: parse, query, set, validate",
                    required=True,
                ),
                ToolParameter(
                    name="source",
                    type="string",
                    description="File path or raw JSON/YAML string",
                    required=True,
                ),
                ToolParameter(
                    name="format",
                    type="string",
                    description="Data format: json or yaml (auto-detect if not specified)",  # noqa: E501
                    required=False,
                    default="auto",
                ),
                ToolParameter(
                    name="query",
                    type="string",
                    description="JSONPath query for 'query' action (e.g., '$.users[0].name')",  # noqa: E501
                    required=False,
                ),
                ToolParameter(
                    name="path",
                    type="string",
                    description="JSONPath for 'set' action",
                    required=False,
                ),
                ToolParameter(
                    name="value",
                    type="string",
                    description="Value to set (will be parsed as JSON)",
                    required=False,
                ),
                ToolParameter(
                    name="output_path",
                    type="string",
                    description="File path to write modified data",
                    required=False,
                ),
                ToolParameter(
                    name="pretty",
                    type="boolean",
                    description="Pretty print output (default: true)",
                    required=False,
                    default=True,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute JSON/YAML operations."""
        action = kwargs.get("action", "").lower()
        source = kwargs.get("source", "")
        format_type = kwargs.get("format", "auto").lower()
        query = kwargs.get("query")
        path = kwargs.get("path")
        value = kwargs.get("value")
        output_path = kwargs.get("output_path")
        pretty = kwargs.get("pretty", True)

        if not action:
            return ToolResult(
                success=False, output="", error="Action parameter is required"
            )

        if not source:
            return ToolResult(
                success=False, output="", error="Source parameter is required"
            )

        valid_actions = ["parse", "query", "set", "validate"]
        if action not in valid_actions:
            return ToolResult(
                success=False,
                output="",
                error=f"Invalid action. Must be one of: {', '.join(valid_actions)}",
            )

        try:
            # Load the data
            data, detected_format = await self._load_data(source, format_type)

            # Perform the action
            if action == "parse":
                result = await self._action_parse(data, detected_format, pretty)
            elif action == "query":
                if not query:
                    return ToolResult(
                        success=False,
                        output="",
                        error="Query parameter is required for 'query' action",
                    )
                result = await self._action_query(data, query)
            elif action == "set":
                if not path:
                    return ToolResult(
                        success=False,
                        output="",
                        error="Path parameter is required for 'set' action",
                    )
                if value is None:
                    return ToolResult(
                        success=False,
                        output="",
                        error="Value parameter is required for 'set' action",
                    )
                result = await self._action_set(
                    data, path, value, detected_format, output_path, pretty
                )
            elif action == "validate":
                result = await self._action_validate(data, detected_format)

            return result

        except Exception as e:
            return ToolResult(
                success=False, output="", error=f"Error processing data: {str(e)}"
            )

    async def _load_data(self, source: str, format_type: str) -> Tuple[Any, str]:
        """Load data from file or string."""
        # Check if source is a file path
        source_path = Path(source)
        if source_path.exists() and source_path.is_file():
            with open(source_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Auto-detect format from file extension if needed
            if format_type == "auto":
                if source_path.suffix.lower() in [".json"]:
                    format_type = "json"
                elif source_path.suffix.lower() in [".yaml", ".yml"]:
                    format_type = "yaml"
        else:
            content = source

        # Try to parse the content
        if format_type == "json" or format_type == "auto":
            try:
                data = json.loads(content)
                return data, "json"
            except json.JSONDecodeError:
                if format_type == "json":
                    raise ValueError("Invalid JSON format")

        if format_type == "yaml" or format_type == "auto":
            try:
                data = yaml.safe_load(content)
                return data, "yaml"
            except yaml.YAMLError as e:
                if format_type == "yaml":
                    raise ValueError(f"Invalid YAML format: {e}")
                else:
                    raise ValueError("Could not parse as JSON or YAML")

        raise ValueError(f"Unknown format: {format_type}")

    async def _action_parse(
        self, data: Any, format_type: str, pretty: bool
    ) -> ToolResult:
        """Parse and return the data structure."""
        if format_type == "json":
            if pretty:
                output = json.dumps(data, indent=2, sort_keys=True)
            else:
                output = json.dumps(data)
        else:  # yaml
            output = yaml.dump(data, default_flow_style=not pretty, sort_keys=True)

        return ToolResult(
            success=True,
            output=output,
            metadata={
                "format": format_type,
                "type": type(data).__name__,
                "size": len(str(data)),
            },
        )

    async def _action_query(self, data: Any, query: str) -> ToolResult:
        """Query data using JSONPath."""
        try:
            jsonpath_expr = jsonpath_parse(query)
            matches = jsonpath_expr.find(data)

            if not matches:
                return ToolResult(
                    success=True, output="null", metadata={"query": query, "matches": 0}
                )

            # Extract values from matches
            if len(matches) == 1:
                result = matches[0].value
            else:
                result = [match.value for match in matches]

            output = json.dumps(result, indent=2)

            return ToolResult(
                success=True,
                output=output,
                metadata={
                    "query": query,
                    "matches": len(matches),
                    "type": type(result).__name__,
                },
            )

        except JsonPathParserError as e:
            return ToolResult(
                success=False, output="", error=f"Invalid JSONPath query: {e}"
            )

    async def _action_set(
        self,
        data: Any,
        path: str,
        value: str,
        format_type: str,
        output_path: Optional[str],
        pretty: bool,
    ) -> ToolResult:
        """Set a value at the specified path."""
        try:
            # Parse the value as JSON
            try:
                parsed_value = json.loads(value)
            except json.JSONDecodeError:
                # If not valid JSON, treat as string
                parsed_value = value

            # Parse JSONPath
            jsonpath_expr = jsonpath_parse(path)
            matches = jsonpath_expr.find(data)

            if not matches:
                return ToolResult(
                    success=False, output="", error=f"Path not found: {path}"
                )

            # Update the value(s)
            updated_count = 0
            for match in matches:
                match.full_path.update(data, parsed_value)
                updated_count += 1

            # Format output
            if format_type == "json":
                if pretty:
                    output = json.dumps(data, indent=2, sort_keys=True)
                else:
                    output = json.dumps(data)
            else:  # yaml
                output = yaml.dump(data, default_flow_style=not pretty, sort_keys=True)

            # Write to file if specified
            if output_path:
                output_file = Path(output_path)
                output_file.parent.mkdir(parents=True, exist_ok=True)
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(output)

            return ToolResult(
                success=True,
                output=output,
                metadata={
                    "path": path,
                    "updated_count": updated_count,
                    "output_file": str(output_path) if output_path else None,
                },
            )

        except JsonPathParserError as e:
            return ToolResult(success=False, output="", error=f"Invalid JSONPath: {e}")

    async def _action_validate(self, data: Any, format_type: str) -> ToolResult:
        """Validate the data structure."""

        def analyze_structure(obj: Any, path: str = "$") -> Dict[str, Any]:
            """Recursively analyze data structure."""
            result: Dict[str, Any] = {"path": path, "type": type(obj).__name__}

            if isinstance(obj, dict):
                result["keys"] = list(obj.keys())
                result["children"] = {}
                for key, value in obj.items():
                    result["children"][key] = analyze_structure(value, f"{path}.{key}")
            elif isinstance(obj, list):
                result["length"] = len(obj)
                if obj:
                    # Analyze first element as sample
                    result["sample"] = analyze_structure(obj[0], f"{path}[0]")
            elif isinstance(obj, str):
                result["length"] = len(obj)
            elif isinstance(obj, (int, float)):
                result["value"] = obj
            elif obj is None:
                result["value"] = None
            elif isinstance(obj, bool):
                result["value"] = obj

            return result

        structure = analyze_structure(data)

        return ToolResult(
            success=True,
            output=json.dumps(structure, indent=2),
            metadata={
                "format": format_type,
                "valid": True,
                "root_type": type(data).__name__,
            },
        )
