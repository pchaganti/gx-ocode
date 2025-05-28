"""
Base classes for OCode tools.
"""

import logging
import traceback
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Coroutine, Dict, List, Optional, Union


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
    category: str = "General"  # Default category for backward compatibility

    def to_ollama_format(self) -> Dict[str, Any]:
        """Convert to Ollama function calling format."""
        properties = {}
        required = []

        for param in self.parameters:
            properties[param.name] = {
                "type": param.type,
                "description": param.description,
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
                    "required": required,
                },
            },
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


class ErrorType(Enum):
    """Standard error types for consistent error handling."""

    VALIDATION_ERROR = "validation_error"
    PERMISSION_ERROR = "permission_error"
    FILE_NOT_FOUND = "file_not_found"
    TIMEOUT_ERROR = "timeout_error"
    RESOURCE_ERROR = "resource_error"
    NETWORK_ERROR = "network_error"
    SECURITY_ERROR = "security_error"
    INTERNAL_ERROR = "internal_error"


class ToolError(Exception):
    """Base exception for tool-specific errors."""

    def __init__(
        self,
        message: str,
        error_type: ErrorType = ErrorType.INTERNAL_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.error_type = error_type
        self.details = details or {}


class ErrorHandler:
    """Centralized error handling utilities for tools."""

    @staticmethod
    def handle_exception(e: Exception, context: str = "") -> ToolResult:
        """Convert any exception to a standardized ToolResult."""
        if isinstance(e, ToolError):
            error_msg = str(e)
            metadata = {
                "error_type": e.error_type.value,
                "context": context,
                **e.details,
            }
        elif isinstance(e, FileNotFoundError):
            error_msg = f"File not found: {str(e)}"
            metadata = {
                "error_type": ErrorType.FILE_NOT_FOUND.value,
                "context": context,
            }
        elif isinstance(e, PermissionError):
            error_msg = f"Permission denied: {str(e)}"
            metadata = {
                "error_type": ErrorType.PERMISSION_ERROR.value,
                "context": context,
            }
        elif isinstance(e, TimeoutError):
            error_msg = f"Operation timed out: {str(e)}"
            metadata = {"error_type": ErrorType.TIMEOUT_ERROR.value, "context": context}
        elif isinstance(e, (OSError, IOError)):
            error_msg = f"I/O error: {str(e)}"
            metadata = {
                "error_type": ErrorType.RESOURCE_ERROR.value,
                "context": context,
            }
        else:
            error_msg = f"Unexpected error: {str(e)}"
            metadata = {
                "error_type": ErrorType.INTERNAL_ERROR.value,
                "context": context,
                "exception_type": type(e).__name__,
            }

        # Log error with stack trace for debugging
        logging.error(f"Tool error in {context}: {error_msg}", exc_info=True)

        return ToolResult(success=False, output="", error=error_msg, metadata=metadata)

    @staticmethod
    def validate_required_params(
        kwargs: Dict[str, Any], required_params: List[str]
    ) -> Optional[ToolResult]:
        """Validate that required parameters are present."""
        missing_params = [
            param
            for param in required_params
            if param not in kwargs or kwargs[param] is None
        ]

        if missing_params:
            return ToolResult(
                success=False,
                output="",
                error=f"Missing required parameters: {', '.join(missing_params)}",
                metadata={
                    "error_type": ErrorType.VALIDATION_ERROR.value,
                    "missing_params": missing_params,
                },
            )
        return None

    @staticmethod
    def validate_string_param(
        value: Any,
        param_name: str,
        min_length: int = 0,
        max_length: int = 10000,
        pattern: Optional[str] = None,
    ) -> Optional[ToolResult]:
        """Validate string parameter with length and pattern constraints."""
        if not isinstance(value, str):
            return ErrorHandler.create_error_result(
                f"Parameter '{param_name}' must be a string, got {type(value).__name__}",
                ErrorType.VALIDATION_ERROR,
                {"param_name": param_name, "actual_type": type(value).__name__},
            )

        if len(value) < min_length:
            return ErrorHandler.create_error_result(
                f"Parameter '{param_name}' must be at least {min_length} characters, got {len(value)}",
                ErrorType.VALIDATION_ERROR,
                {
                    "param_name": param_name,
                    "actual_length": len(value),
                    "min_length": min_length,
                },
            )

        if len(value) > max_length:
            return ErrorHandler.create_error_result(
                f"Parameter '{param_name}' must be at most {max_length} characters, got {len(value)}",
                ErrorType.VALIDATION_ERROR,
                {
                    "param_name": param_name,
                    "actual_length": len(value),
                    "max_length": max_length,
                },
            )

        if pattern:
            import re

            if not re.match(pattern, value):
                return ErrorHandler.create_error_result(
                    f"Parameter '{param_name}' does not match required pattern",
                    ErrorType.VALIDATION_ERROR,
                    {"param_name": param_name, "pattern": pattern},
                )

        return None

    @staticmethod
    def create_success_result(
        output: str, metadata: Optional[Dict[str, Any]] = None
    ) -> ToolResult:
        """Create a standardized success result."""
        return ToolResult(success=True, output=output, metadata=metadata or {})

    @staticmethod
    def create_error_result(
        error_msg: str,
        error_type: ErrorType = ErrorType.INTERNAL_ERROR,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ToolResult:
        """Create a standardized error result."""
        result_metadata = {"error_type": error_type.value}
        if metadata:
            result_metadata.update(metadata)

        return ToolResult(
            success=False, output="", error=error_msg, metadata=result_metadata
        )


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
            param_def = next(
                (p for p in definition.parameters if p.name == param_name), None
            )
            if param_def:
                # Special case: for memory tools, "value" parameter can be any type
                if (
                    param_name == "value"
                    and param_def.description
                    and "JSON-serializable" in param_def.description
                ):
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
        from .agent_tool import AgentTool
        from .architect_tool import ArchitectTool
        from .bash_tool import BashTool, ScriptTool
        from .curl_tool import CurlTool
        from .data_tools import JsonYamlTool
        from .diff_tool import DiffTool
        from .env_tool import EnvironmentTool
        from .file_edit_tool import FileEditTool
        from .file_ops_tool import CopyTool, MoveTool, RemoveTool
        from .file_tools import FileListTool, FileReadTool, FileWriteTool
        from .find_tool import FindTool
        from .git_tools import GitCommitTool, GitDiffTool, GitStatusTool
        from .glob_tool import AdvancedGlobTool, GlobTool
        from .grep_tool import CodeGrepTool, GrepTool

        # Basic Unix tools
        from .head_tail_tool import HeadTool, TailTool
        from .ls_tool import LsTool
        from .mcp_tool import MCPTool
        from .memory_tools import MemoryReadTool, MemoryWriteTool
        from .notebook_tools import NotebookEditTool, NotebookReadTool
        from .ping_tool import PingTool
        from .process_tool import ProcessMonitorTool
        from .shell_tools import ShellCommandTool
        from .sticker_tool import StickerRequestTool
        from .test_tools import ExecutionTool
        from .text_tools import SortTool, UniqTool
        from .think_tool import ThinkTool
        from .wc_tool import WcTool
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
            PingTool(),
            # Data processing and system tools
            JsonYamlTool(),
            ProcessMonitorTool(),
            EnvironmentTool(),
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

    async def execute_tool(self, tool_name: str, **kwargs) -> ToolResult:
        """Execute a tool by name."""
        tool = self.get_tool(tool_name)
        if not tool:
            return ToolResult(
                success=False, output="", error=f"Tool '{tool_name}' not found"
            )

        if not tool.validate_parameters(kwargs):
            return ToolResult(
                success=False,
                output="",
                error=f"Invalid parameters for tool '{tool_name}'",
            )

        try:
            return await tool.execute(**kwargs)
        except Exception as e:
            return ToolResult(
                success=False, output="", error=f"Tool execution failed: {str(e)}"
            )
