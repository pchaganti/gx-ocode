# Tools API Reference

Complete API documentation for OCode's tool system.

## Base Classes

### Tool (Abstract Base Class)

```python
from abc import ABC, abstractmethod
from typing import Any, Dict
from ocode_python.tools.base import Tool, ToolDefinition, ToolResult

class Tool(ABC):
    """Abstract base class for all tools."""

    @property
    @abstractmethod
    def definition(self) -> ToolDefinition:
        """Return tool definition with metadata."""
        pass

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute tool with given parameters."""
        pass
```

### ToolDefinition

```python
@dataclass
class ToolDefinition:
    """Tool metadata and parameter definitions."""

    name: str                          # Unique tool identifier
    description: str                   # Human-readable description
    parameters: List[ToolParameter]    # Parameter definitions
    category: str = "general"          # Tool category for organization
    required_permissions: List[str] = field(default_factory=list)

    def to_ollama_format(self) -> Dict[str, Any]:
        """Convert to Ollama function calling format."""
```

### ToolParameter

```python
@dataclass
class ToolParameter:
    """Parameter definition for tools."""

    name: str                      # Parameter name
    description: str               # Parameter description
    type: str                      # Type: string, integer, boolean, array, object
    required: bool = True          # Whether parameter is required
    default: Any = None           # Default value if not required
    enum: List[Any] = None        # Allowed values
    items: Dict[str, Any] = None  # Array item schema
    properties: Dict[str, Any] = None  # Object properties
```

### ToolResult

```python
@dataclass
class ToolResult:
    """Standard result format for all tools."""

    success: bool              # Whether operation succeeded
    output: str               # Result output (stdout)
    error: str = ""           # Error message if failed
    metadata: Dict[str, Any] = field(default_factory=dict)
```

## File Operation Tools

### file_read

Read file contents with line numbers.

```python
# Definition
ToolDefinition(
    name="file_read",
    description="Read the contents of a file",
    parameters=[
        ToolParameter(
            name="path",
            description="Path to the file to read",
            type="string",
            required=True
        ),
        ToolParameter(
            name="start_line",
            description="Line number to start reading from",
            type="integer",
            required=False,
            default=1
        ),
        ToolParameter(
            name="end_line",
            description="Line number to stop reading at",
            type="integer",
            required=False
        )
    ],
    category="file_operations",
    required_permissions=["file_read"]
)

# Usage
result = await file_read_tool.execute(
    path="/path/to/file.py",
    start_line=10,
    end_line=20
)

# Result
ToolResult(
    success=True,
    output="10 | def process():\n11 |     pass\n...",
    error=""
)
```

### file_write

Create or overwrite files.

```python
# Definition
ToolDefinition(
    name="file_write",
    description="Write content to a file",
    parameters=[
        ToolParameter(
            name="path",
            description="Path where to write the file",
            type="string",
            required=True
        ),
        ToolParameter(
            name="content",
            description="Content to write",
            type="string",
            required=True
        ),
        ToolParameter(
            name="create_dirs",
            description="Create parent directories if needed",
            type="boolean",
            required=False,
            default=True
        )
    ],
    category="file_operations",
    required_permissions=["file_write"]
)
```

### file_edit

Make precise edits to existing files.

```python
# Definition
ToolDefinition(
    name="file_edit",
    description="Edit specific parts of a file",
    parameters=[
        ToolParameter(
            name="path",
            description="Path to file to edit",
            type="string",
            required=True
        ),
        ToolParameter(
            name="old_text",
            description="Exact text to replace",
            type="string",
            required=True
        ),
        ToolParameter(
            name="new_text",
            description="New text to insert",
            type="string",
            required=True
        ),
        ToolParameter(
            name="occurrence",
            description="Which occurrence to replace (0=all)",
            type="integer",
            required=False,
            default=0
        )
    ]
)
```

### file_ops

File operations: copy, move, remove.

```python
# Definition
ToolDefinition(
    name="file_ops",
    description="Perform file operations",
    parameters=[
        ToolParameter(
            name="operation",
            description="Operation to perform",
            type="string",
            required=True,
            enum=["copy", "move", "remove"]
        ),
        ToolParameter(
            name="source",
            description="Source file path",
            type="string",
            required=True
        ),
        ToolParameter(
            name="destination",
            description="Destination path (for copy/move)",
            type="string",
            required=False
        )
    ]
)
```

## Text Processing Tools

### grep

Search file contents with regex.

```python
# Definition
ToolDefinition(
    name="grep",
    description="Search for patterns in files",
    parameters=[
        ToolParameter(
            name="pattern",
            description="Regex pattern to search",
            type="string",
            required=True
        ),
        ToolParameter(
            name="path",
            description="Path to search in",
            type="string",
            required=False,
            default="."
        ),
        ToolParameter(
            name="recursive",
            description="Search recursively",
            type="boolean",
            required=False,
            default=True
        ),
        ToolParameter(
            name="ignore_case",
            description="Case insensitive search",
            type="boolean",
            required=False,
            default=False
        ),
        ToolParameter(
            name="file_pattern",
            description="File pattern to match (e.g., *.py)",
            type="string",
            required=False
        )
    ]
)

# Result includes matching lines with context
ToolResult(
    success=True,
    output="file.py:10: def process_data():\nfile.py:20: data = process_data(input)",
    metadata={"match_count": 2, "files_searched": 15}
)
```

### diff

Compare files or strings.

```python
# Definition
ToolDefinition(
    name="diff",
    description="Compare two files or strings",
    parameters=[
        ToolParameter(
            name="source1",
            description="First file path or string",
            type="string",
            required=True
        ),
        ToolParameter(
            name="source2",
            description="Second file path or string",
            type="string",
            required=True
        ),
        ToolParameter(
            name="unified",
            description="Use unified diff format",
            type="boolean",
            required=False,
            default=True
        ),
        ToolParameter(
            name="context_lines",
            description="Number of context lines",
            type="integer",
            required=False,
            default=3
        )
    ]
)
```

## System Tools

### bash

Execute shell commands (requires permission).

```python
# Definition
ToolDefinition(
    name="bash",
    description="Execute shell commands",
    parameters=[
        ToolParameter(
            name="command",
            description="Command to execute",
            type="string",
            required=True
        ),
        ToolParameter(
            name="working_dir",
            description="Working directory",
            type="string",
            required=False
        ),
        ToolParameter(
            name="timeout",
            description="Timeout in seconds",
            type="integer",
            required=False,
            default=30
        ),
        ToolParameter(
            name="env",
            description="Environment variables",
            type="object",
            required=False
        )
    ],
    required_permissions=["shell_exec"]
)

# Security validation applied
# User confirmation may be required
```

### env

Environment variable management.

```python
# Definition
ToolDefinition(
    name="env",
    description="Manage environment variables",
    parameters=[
        ToolParameter(
            name="action",
            description="Action to perform",
            type="string",
            required=True,
            enum=["get", "set", "list", "delete"]
        ),
        ToolParameter(
            name="name",
            description="Variable name",
            type="string",
            required=False
        ),
        ToolParameter(
            name="value",
            description="Variable value (for set)",
            type="string",
            required=False
        ),
        ToolParameter(
            name="persistent",
            description="Save to .env file",
            type="boolean",
            required=False,
            default=False
        )
    ]
)
```

## Development Tools

### git_status

Check repository status.

```python
# Definition
ToolDefinition(
    name="git_status",
    description="Get git repository status",
    parameters=[
        ToolParameter(
            name="path",
            description="Repository path",
            type="string",
            required=False,
            default="."
        ),
        ToolParameter(
            name="verbose",
            description="Show detailed status",
            type="boolean",
            required=False,
            default=False
        )
    ]
)

# Result
ToolResult(
    success=True,
    output="On branch main\nChanges not staged:\n  modified: file.py",
    metadata={
        "branch": "main",
        "modified_files": ["file.py"],
        "untracked_files": [],
        "staged_files": []
    }
)
```

### test_runner

Execute test suites.

```python
# Definition
ToolDefinition(
    name="test_runner",
    description="Run project tests",
    parameters=[
        ToolParameter(
            name="framework",
            description="Test framework",
            type="string",
            required=False,
            enum=["pytest", "unittest", "jest", "mocha", "cargo"]
        ),
        ToolParameter(
            name="path",
            description="Test path or pattern",
            type="string",
            required=False
        ),
        ToolParameter(
            name="verbose",
            description="Verbose output",
            type="boolean",
            required=False,
            default=False
        ),
        ToolParameter(
            name="coverage",
            description="Generate coverage report",
            type="boolean",
            required=False,
            default=False
        )
    ]
)
```

## Analysis Tools

### architect

Analyze project architecture.

```python
# Definition
ToolDefinition(
    name="architect",
    description="Analyze and visualize project architecture",
    parameters=[
        ToolParameter(
            name="analysis_type",
            description="Type of analysis",
            type="string",
            required=True,
            enum=["overview", "dependencies", "structure", "metrics"]
        ),
        ToolParameter(
            name="path",
            description="Path to analyze",
            type="string",
            required=False,
            default="."
        ),
        ToolParameter(
            name="depth",
            description="Analysis depth",
            type="integer",
            required=False,
            default=3
        ),
        ToolParameter(
            name="output_format",
            description="Output format",
            type="string",
            required=False,
            enum=["text", "json", "mermaid"],
            default="text"
        )
    ]
)
```

### think

Extended reasoning for complex tasks.

```python
# Definition
ToolDefinition(
    name="think",
    description="Deep analysis and reasoning",
    parameters=[
        ToolParameter(
            name="task",
            description="Task to analyze",
            type="string",
            required=True
        ),
        ToolParameter(
            name="context",
            description="Additional context",
            type="string",
            required=False
        ),
        ToolParameter(
            name="approach",
            description="Reasoning approach",
            type="string",
            required=False,
            enum=["step_by_step", "pros_cons", "alternatives"],
            default="step_by_step"
        )
    ]
)
```

## Memory Tools

### memory_read

Retrieve stored information.

```python
# Definition
ToolDefinition(
    name="memory_read",
    description="Read from memory storage",
    parameters=[
        ToolParameter(
            name="key",
            description="Memory key to read",
            type="string",
            required=False
        ),
        ToolParameter(
            name="category",
            description="Memory category",
            type="string",
            required=False
        ),
        ToolParameter(
            name="memory_type",
            description="Type of memory",
            type="string",
            required=False,
            enum=["persistent", "session", "all"],
            default="persistent"
        )
    ]
)
```

### memory_write

Store information persistently.

```python
# Definition
ToolDefinition(
    name="memory_write",
    description="Write to memory storage",
    parameters=[
        ToolParameter(
            name="key",
            description="Memory key",
            type="string",
            required=True
        ),
        ToolParameter(
            name="value",
            description="Value to store",
            type="string",
            required=True
        ),
        ToolParameter(
            name="category",
            description="Category for organization",
            type="string",
            required=False,
            default="general"
        ),
        ToolParameter(
            name="memory_type",
            description="Storage type",
            type="string",
            required=False,
            enum=["persistent", "session"],
            default="persistent"
        ),
        ToolParameter(
            name="operation",
            description="Write operation",
            type="string",
            required=False,
            enum=["set", "append", "delete"],
            default="set"
        )
    ]
)
```

## Data Processing Tools

### json_yaml

Parse and manipulate structured data.

```python
# Definition
ToolDefinition(
    name="json_yaml",
    description="Process JSON and YAML data",
    parameters=[
        ToolParameter(
            name="action",
            description="Action to perform",
            type="string",
            required=True,
            enum=["parse", "validate", "convert", "query", "merge"]
        ),
        ToolParameter(
            name="input",
            description="Input data or file path",
            type="string",
            required=True
        ),
        ToolParameter(
            name="format",
            description="Input format",
            type="string",
            required=False,
            enum=["json", "yaml", "auto"],
            default="auto"
        ),
        ToolParameter(
            name="query",
            description="JSONPath query (for query action)",
            type="string",
            required=False
        ),
        ToolParameter(
            name="output_format",
            description="Output format",
            type="string",
            required=False,
            enum=["json", "yaml", "pretty"],
            default="json"
        )
    ]
)
```

## Integration Tools

### mcp

Model Context Protocol operations.

```python
# Definition
ToolDefinition(
    name="mcp",
    description="MCP server operations",
    parameters=[
        ToolParameter(
            name="action",
            description="MCP action",
            type="string",
            required=True,
            enum=["list", "call", "resource", "prompt"]
        ),
        ToolParameter(
            name="server",
            description="MCP server name",
            type="string",
            required=False
        ),
        ToolParameter(
            name="method",
            description="Method to call",
            type="string",
            required=False
        ),
        ToolParameter(
            name="params",
            description="Method parameters",
            type="object",
            required=False
        )
    ]
)
```

### agent

Delegate tasks to specialized agents.

```python
# Definition
ToolDefinition(
    name="agent",
    description="Create and manage specialized agents",
    parameters=[
        ToolParameter(
            name="action",
            description="Agent action",
            type="string",
            required=True,
            enum=["create", "delegate", "list", "status", "terminate"]
        ),
        ToolParameter(
            name="agent_type",
            description="Type of agent",
            type="string",
            required=False,
            enum=["reviewer", "coder", "tester", "analyzer", "general"]
        ),
        ToolParameter(
            name="task",
            description="Task to delegate",
            type="string",
            required=False
        ),
        ToolParameter(
            name="agent_id",
            description="Agent identifier",
            type="string",
            required=False
        )
    ]
)
```

## Tool Registry

### Registering Tools

```python
from ocode_python.tools.base import ToolRegistry

registry = ToolRegistry()

# Register individual tool
registry.register_tool(MyCustomTool())

# Register core tools
registry.register_core_tools()

# Get tool by name
tool = registry.get_tool("file_read")

# Get all tool definitions
definitions = registry.get_tool_definitions()

# Execute tool
result = await registry.execute_tool(
    "file_read",
    path="/path/to/file.py"
)
```

### Custom Tool Implementation

```python
from ocode_python.tools.base import Tool, ToolDefinition, ToolParameter, ToolResult

class CustomTool(Tool):
    """Custom tool implementation example."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="custom_tool",
            description="Perform custom operation",
            parameters=[
                ToolParameter(
                    name="input",
                    description="Input data",
                    type="string",
                    required=True
                ),
                ToolParameter(
                    name="options",
                    description="Processing options",
                    type="object",
                    required=False,
                    properties={
                        "format": {"type": "string"},
                        "validate": {"type": "boolean"}
                    }
                )
            ],
            category="custom",
            required_permissions=["custom_permission"]
        )

    async def execute(self, **kwargs) -> ToolResult:
        """Execute custom tool logic."""
        try:
            input_data = kwargs.get("input", "")
            options = kwargs.get("options", {})

            # Validate input
            if not input_data:
                return ToolResult(
                    success=False,
                    output="",
                    error="Input is required"
                )

            # Process data
            result = await self._process(input_data, options)

            return ToolResult(
                success=True,
                output=result,
                metadata={"processed_at": time.time()}
            )

        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Processing failed: {str(e)}"
            )

    async def _process(self, data: str, options: dict) -> str:
        """Internal processing logic."""
        # Implementation
        return f"Processed: {data}"
```

## Error Handling

All tools follow consistent error handling:

```python
# Success
ToolResult(
    success=True,
    output="Operation completed successfully",
    metadata={"duration": 1.5}
)

# Failure
ToolResult(
    success=False,
    output="",  # Empty on failure
    error="File not found: /path/to/file.txt"
)

# Partial success
ToolResult(
    success=True,
    output="Processed 9 of 10 files",
    error="Warning: 1 file skipped due to permissions",
    metadata={"processed": 9, "skipped": 1}
)
```

## Security Model

### Permission Requirements

```python
# Tool definition with permissions
ToolDefinition(
    name="dangerous_tool",
    description="Potentially dangerous operation",
    parameters=[...],
    required_permissions=["shell_exec", "file_write"]
)

# Runtime permission check
if not security_manager.has_permission("shell_exec"):
    return ToolResult(
        success=False,
        output="",
        error="Permission denied: shell_exec required"
    )
```

### Path Validation

```python
# Automatic path validation for file tools
validated_path = security_manager.validate_path(
    requested_path,
    operation="read"
)
# Raises SecurityError if path not allowed
```

### Command Sanitization

```python
# Shell commands are sanitized
safe_command = security_manager.sanitize_command(
    user_command,
    allowed_commands=config.allowed_commands
)
# Returns None if command not allowed
```

## Performance Considerations

### Async Execution

All tools use async/await for non-blocking I/O:

```python
# Good - async file reading
async with aiofiles.open(path) as f:
    content = await f.read()

# Bad - blocking file reading
with open(path) as f:
    content = f.read()  # Blocks event loop
```

### Streaming Large Data

```python
# Stream large files
async def read_large_file(path: Path):
    async with aiofiles.open(path) as f:
        async for line in f:
            yield line
```

### Caching

```python
# Tools can use caching
@cached(ttl=3600)
async def expensive_operation(params):
    # Cached for 1 hour
    return await process(params)
```

## Testing Tools

### Unit Testing

```python
import pytest
from ocode_python.tools.your_tool import YourTool

@pytest.mark.asyncio
async def test_tool_execution():
    tool = YourTool()

    # Test successful execution
    result = await tool.execute(
        input="test data",
        options={"validate": True}
    )

    assert result.success
    assert "expected output" in result.output
    assert result.metadata["processed_at"] > 0

    # Test error handling
    result = await tool.execute(input="")

    assert not result.success
    assert result.error == "Input is required"
```

### Integration Testing

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_tool_with_filesystem(tmp_path):
    # Create test file
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")

    # Test file tool
    tool = FileReadTool()
    result = await tool.execute(path=str(test_file))

    assert result.success
    assert "test content" in result.output
```

## Version Compatibility

- **v2.0+**: Current API as documented
- **v1.x**: Legacy API with different parameter names
- **Migration**: Use compatibility layer for v1.x tools

```python
# Compatibility wrapper
from ocode_python.tools.compat import v1_to_v2_tool

legacy_tool = LegacyToolV1()
modern_tool = v1_to_v2_tool(legacy_tool)
```
