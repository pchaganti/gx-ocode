"""
Base classes for OCode tools.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Coroutine
from dataclasses import dataclass

@dataclass
class ToolParameter:
    """Tool parameter definition."""
    name: str
    type: str  # "string", "number", "boolean", "array", "object"
    description: str
    required: bool = True
    default: Optional[Any] = None

@dataclass
class ToolDefinition:
    """Tool definition for LLM function calling."""
    name: str
    description: str
    parameters: List[ToolParameter]

    def to_ollama_format(self) -> Dict[str, Any]:
        """Convert to Ollama function calling format."""
        properties = {}
        required = []

        for param in self.parameters:
            properties[param.name] = {
                "type": param.type,
                "description": param.description
            }

            if param.default is not None:
                properties[param.name]["default"] = param.default

            if param.required:
                required.append(param.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        }

@dataclass
class ToolResult:
    """Result from tool execution."""
    success: bool
    output: str
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def __str__(self) -> str:
        if self.success:
            return self.output
        else:
            return f"Error: {self.error}"

class Tool(ABC):
    """
    Base class for all OCode tools.

    Tools are functions that can be called by the AI to perform specific tasks
    like reading files, running git commands, executing shell commands, etc.
    """

    def __init__(self):
        self.name = self.definition.name

    @property
    @abstractmethod
    def definition(self) -> ToolDefinition:
        """Get tool definition for LLM function calling."""
        pass

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the tool with given parameters."""
        pass

    def validate_parameters(self, kwargs: Dict[str, Any]) -> bool:
        """Validate parameters against tool definition."""
        definition = self.definition

        # Check required parameters
        for param in definition.parameters:
            if param.required and param.name not in kwargs:
                return False

        # Check parameter types (basic validation)
        for param_name, value in kwargs.items():
            param_def = next((p for p in definition.parameters if p.name == param_name), None)
            if param_def:
                # Special case: for memory tools, "value" parameter can be any type
                if param_name == "value" and param_def.description and "JSON-serializable" in param_def.description:
                    continue  # Allow any JSON-serializable type
                elif param_def.type == "string" and not isinstance(value, str):
                    return False
                elif param_def.type == "number" and not isinstance(value, (int, float)):
                    return False
                elif param_def.type == "boolean" and not isinstance(value, bool):
                    return False
                elif param_def.type == "array" and not isinstance(value, list):
                    return False
                elif param_def.type == "object" and not isinstance(value, dict):
                    return False

        return True

class ToolRegistry:
    """
    Registry for managing and executing tools.
    """

    def __init__(self):
        self.tools: Dict[str, Tool] = {}

    def register(self, tool: Tool):
        """Register a tool."""
        self.tools[tool.name] = tool

    def register_core_tools(self):
        """Register all core tools."""
        from .file_tools import FileReadTool, FileWriteTool, FileListTool
        from .git_tools import GitStatusTool, GitCommitTool, GitDiffTool
        from .shell_tools import ShellCommandTool
        from .test_tools import ExecutionTool
        from .glob_tool import GlobTool, AdvancedGlobTool
        from .grep_tool import GrepTool, CodeGrepTool
        from .ls_tool import LsTool
        from .file_edit_tool import FileEditTool
        from .bash_tool import BashTool, ScriptTool
        from .notebook_tools import NotebookReadTool, NotebookEditTool
        from .memory_tools import MemoryReadTool, MemoryWriteTool
        from .think_tool import ThinkTool
        from .architect_tool import ArchitectTool
        from .agent_tool import AgentTool
        from .mcp_tool import MCPTool
        from .sticker_tool import StickerRequestTool
        # Basic Unix tools
        from .head_tail_tool import HeadTool, TailTool
        from .diff_tool import DiffTool
        from .wc_tool import WcTool
        from .find_tool import FindTool
        from .file_ops_tool import CopyTool, MoveTool, RemoveTool
        from .text_tools import SortTool, UniqTool
        from .curl_tool import CurlTool
        from .which_tool import WhichTool

        core_tools = [
            # Original tools
            FileReadTool(),
            FileWriteTool(),
            FileListTool(),
            GitStatusTool(),
            GitCommitTool(),
            GitDiffTool(),
            ShellCommandTool(),
            ExecutionTool(),
            # New enhanced tools
            GlobTool(),
            AdvancedGlobTool(),
            GrepTool(),
            CodeGrepTool(),
            LsTool(),
            FileEditTool(),
            BashTool(),
            ScriptTool(),
            NotebookReadTool(),
            NotebookEditTool(),
            MemoryReadTool(),
            MemoryWriteTool(),
            ThinkTool(),
            ArchitectTool(),
            AgentTool(),
            MCPTool(),
            StickerRequestTool(),
            # Basic Unix tools
            HeadTool(),
            TailTool(),
            DiffTool(),
            WcTool(),
            FindTool(),
            CopyTool(),
            MoveTool(),
            RemoveTool(),
            SortTool(),
            UniqTool(),
            CurlTool(),
            WhichTool(),
        ]

        for tool in core_tools:
            self.register(tool)

    def get_tool(self, name: str) -> Optional[Tool]:
        """Get tool by name."""
        return self.tools.get(name)

    def get_all_tools(self) -> List[Tool]:
        """Get all registered tools."""
        return list(self.tools.values())

    def get_tool_definitions(self) -> List[Dict[str, Any]]:
        """Get all tool definitions in Ollama format."""
        return [tool.definition.to_ollama_format() for tool in self.tools.values()]

    async def execute_tool(self, name: str, **kwargs) -> ToolResult:
        """Execute a tool by name."""
        tool = self.get_tool(name)
        if not tool:
            return ToolResult(
                success=False,
                output="",
                error=f"Tool '{name}' not found"
            )

        if not tool.validate_parameters(kwargs):
            return ToolResult(
                success=False,
                output="",
                error=f"Invalid parameters for tool '{name}'"
            )

        try:
            return await tool.execute(**kwargs)
        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Tool execution failed: {str(e)}"
            )
