"""
Head and tail tools for viewing file contents.
"""

import collections
from typing import Deque

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

# File size limit for safety (100MB)
MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024


class HeadTool(Tool):
    """Tool for viewing the first N lines of a file."""

    @property
    def definition(self) -> ToolDefinition:
        """Define the head tool specification.

        Returns:
            ToolDefinition with parameters for displaying the first N lines
            of a file.
        """
        return ToolDefinition(
            name="head",
            description="Display the first lines of a file",
            parameters=[
                ToolParameter(
                    name="file_path",
                    type="string",
                    description="Path to the file to read",
                    required=True,
                ),
                ToolParameter(
                    name="lines",
                    type="number",
                    description="Number of lines to display (default: 10)",
                    required=False,
                    default=10,
                ),
            ],
        )

    async def execute(self, **kwargs) -> ToolResult:
        """Execute head command."""
        try:
            # Validate required parameters
            validation_error = ErrorHandler.validate_required_params(
                kwargs, ["file_path"]
            )
            if validation_error:
                return validation_error

            file_path = kwargs.get("file_path")
            lines = kwargs.get("lines", 10)

            # Validate file_path type
            if not isinstance(file_path, str):
                return ErrorHandler.create_error_result(
                    "File path parameter must be a string", ErrorType.VALIDATION_ERROR
                )

            # Validate path
            is_valid, error_msg, normalized_path = path_validator.validate_path(
                file_path, check_exists=True
            )
            if not is_valid or normalized_path is None:
                return ErrorHandler.create_error_result(
                    f"Invalid path: {error_msg}", ErrorType.VALIDATION_ERROR
                )

            # At this point normalized_path is guaranteed to be non-None
            assert normalized_path is not None  # Type safety for MyPy
            path = normalized_path

            if not path.is_file():
                return ErrorHandler.create_error_result(
                    f"Not a file: {file_path}", ErrorType.VALIDATION_ERROR
                )

            # Check file size (limit to 100MB for safety)
            file_size = path.stat().st_size
            if file_size > MAX_FILE_SIZE_BYTES:
                return ErrorHandler.create_error_result(
                    f"File too large: {file_size / (1024*1024):.1f}MB (max 100MB)",
                    ErrorType.RESOURCE_ERROR,
                )

            # Read first N lines with timeout and proper resource management
            try:
                async with async_timeout(30):  # 30 second timeout
                    with open(path, "r", encoding="utf-8", errors="replace") as f:
                        file_lines = []
                        for i, line in enumerate(f):
                            if i >= lines:
                                break
                            file_lines.append(line.rstrip("\n\r"))
            except UnicodeDecodeError as e:
                return ErrorHandler.create_error_result(
                    f"Encoding error reading file: {str(e)}", ErrorType.VALIDATION_ERROR
                )
            except OSError as e:
                return ErrorHandler.create_error_result(
                    f"I/O error reading file: {str(e)}", ErrorType.RESOURCE_ERROR
                )

            output = "\n".join(file_lines)
            return ErrorHandler.create_success_result(
                output, metadata={"file": str(path), "lines_shown": len(file_lines)}
            )

        except Exception as e:
            return ErrorHandler.handle_exception(e, "head_tool")


class TailTool(Tool):
    """Tool for viewing the last N lines of a file."""

    @property
    def definition(self) -> ToolDefinition:
        """Define the tail tool specification.

        Returns:
            ToolDefinition with parameters for displaying the last N lines
            of a file with optional follow mode.
        """
        return ToolDefinition(
            name="tail",
            description="Display the last lines of a file",
            parameters=[
                ToolParameter(
                    name="file_path",
                    type="string",
                    description="Path to the file to read",
                    required=True,
                ),
                ToolParameter(
                    name="lines",
                    type="number",
                    description="Number of lines to display (default: 10)",
                    required=False,
                    default=10,
                ),
            ],
        )

    async def execute(self, **kwargs) -> ToolResult:
        """Execute tail command."""
        try:
            # Validate required parameters
            validation_error = ErrorHandler.validate_required_params(
                kwargs, ["file_path"]
            )
            if validation_error:
                return validation_error

            file_path = kwargs.get("file_path")
            lines = kwargs.get("lines", 10)

            # Validate file_path type
            if not isinstance(file_path, str):
                return ErrorHandler.create_error_result(
                    "File path parameter must be a string", ErrorType.VALIDATION_ERROR
                )

            # Validate path
            is_valid, error_msg, normalized_path = path_validator.validate_path(
                file_path, check_exists=True
            )
            if not is_valid or normalized_path is None:
                return ErrorHandler.create_error_result(
                    f"Invalid path: {error_msg}", ErrorType.VALIDATION_ERROR
                )

            # At this point normalized_path is guaranteed to be non-None
            assert normalized_path is not None  # Type safety for MyPy
            path = normalized_path

            if not path.is_file():
                return ErrorHandler.create_error_result(
                    f"Not a file: {file_path}", ErrorType.VALIDATION_ERROR
                )

            # Check file size (limit to 100MB for safety)
            file_size = path.stat().st_size
            if file_size > MAX_FILE_SIZE_BYTES:
                return ErrorHandler.create_error_result(
                    f"File too large: {file_size / (1024*1024):.1f}MB (max 100MB)",
                    ErrorType.RESOURCE_ERROR,
                )

            # Read last N lines efficiently with timeout and proper resource management
            try:
                async with async_timeout(30):  # 30 second timeout
                    # Use deque for memory-efficient tail operation
                    buffer: Deque[str] = collections.deque(maxlen=lines)
                    with open(path, "r", encoding="utf-8", errors="replace") as f:
                        for line in f:
                            buffer.append(line.rstrip("\n\r"))
            except UnicodeDecodeError as e:
                return ErrorHandler.create_error_result(
                    f"Encoding error reading file: {str(e)}", ErrorType.VALIDATION_ERROR
                )
            except OSError as e:
                return ErrorHandler.create_error_result(
                    f"I/O error reading file: {str(e)}", ErrorType.RESOURCE_ERROR
                )

            # Convert deque to list for output
            output_lines = list(buffer)
            output = "\n".join(output_lines)

            return ErrorHandler.create_success_result(
                output,
                metadata={
                    "file": str(path),
                    "lines_shown": len(output_lines),
                    "memory_efficient": True,
                },
            )

        except Exception as e:
            return ErrorHandler.handle_exception(e, "tail_tool")
