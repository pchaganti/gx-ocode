"""
File manipulation tools.
"""

import os
import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
import re

from .base import Tool, ToolDefinition, ToolParameter, ToolResult, ErrorHandler, ErrorType, ToolError


class PathValidator:
    """Utility class for validating and sanitizing file paths."""
    
    def __init__(self, allowed_base_paths: Optional[List[str]] = None, max_path_length: int = 4096):
        self.allowed_base_paths = allowed_base_paths or [os.getcwd()]
        self.max_path_length = max_path_length
    
    def validate_path(self, path: str, allow_creation: bool = False) -> Tuple[bool, str, Optional[Path]]:
        """
        Validate a file path for security and correctness.
        
        Returns: (is_valid, error_message, resolved_path)
        """
        try:
            # Basic validation
            if not path or len(path) > self.max_path_length:
                return False, f"Invalid path length: {len(path) if path else 0}", None
            
            # Check for suspicious patterns
            suspicious_patterns = [
                r"\.\.[\\/]",  # Directory traversal
                r"[\x00-\x1f]",  # Control characters
                r"^[\\/]proc[\\/]",  # /proc access
                r"^[\\/]sys[\\/]",  # /sys access  
                r"^[\\/]dev[\\/]",  # /dev access
                r"[\\/]etc[\\/]passwd",  # passwd file
                r"[\\/]etc[\\/]shadow",  # shadow file
            ]
            
            for pattern in suspicious_patterns:
                if re.search(pattern, path, re.IGNORECASE):
                    return False, f"Path contains suspicious pattern: {pattern}", None
            
            # Resolve the path
            try:
                resolved_path = Path(path).resolve()
            except (OSError, ValueError) as e:
                return False, f"Path resolution failed: {e}", None
            
            # Check if path is within allowed base paths
            path_is_allowed = False
            for base_path in self.allowed_base_paths:
                try:
                    resolved_base = Path(base_path).resolve()
                    # Check if the resolved path is within the base path
                    resolved_path.relative_to(resolved_base)
                    path_is_allowed = True
                    break
                except ValueError:
                    continue
            
            if not path_is_allowed:
                return False, f"Path is outside allowed directories: {self.allowed_base_paths}", None
            
            # Check if path exists (if not allowing creation)
            if not allow_creation and not resolved_path.exists():
                return False, f"Path does not exist: {resolved_path}", None
            
            return True, "", resolved_path
            
        except Exception as e:
            return False, f"Path validation error: {e}", None

class FileReadTool(Tool):
    """Tool for reading file contents."""
    
    def __init__(self):
        super().__init__()
        self.path_validator = PathValidator()

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="file_read",
            description="Read the contents of a file",
            category="File Operations",
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path to the file to read",
                    required=True
                ),
                ToolParameter(
                    name="encoding",
                    type="string",
                    description="File encoding (default: utf-8)",
                    required=False,
                    default="utf-8"
                )
            ]
        )

    def _try_common_extensions(self, base_path: Path) -> Optional[Path]:
        """Try common file extensions if the base path doesn't exist."""
        if base_path.exists():
            return base_path

        # Common extensions to try
        common_extensions = ['.md', '.txt', '.rst', '.markdown']
        
        for ext in common_extensions:
            path_with_ext = base_path.with_suffix(ext)
            if path_with_ext.exists():
                return path_with_ext
        
        return None

    async def execute(self, **kwargs: Any) -> ToolResult:  # type: ignore[override]
        """Read file contents with enhanced security validation."""
        try:
            # Validate required parameters
            validation_error = ErrorHandler.validate_required_params(kwargs, ['path'])
            if validation_error:
                return validation_error
            
            path = kwargs.get('path')
            encoding = kwargs.get('encoding', 'utf-8')
            
            # Validate path security
            is_valid, error_msg, validated_path = self.path_validator.validate_path(path, allow_creation=False)
            if not is_valid:
                return ErrorHandler.create_error_result(
                    f"Path validation failed: {error_msg}",
                    ErrorType.SECURITY_ERROR,
                    {"path": path}
                )

            # Try to find the file with common extensions if it doesn't exist
            resolved_path = self._try_common_extensions(validated_path)
            if not resolved_path:
                return ErrorHandler.create_error_result(
                    f"File does not exist: {path} (tried with common extensions: .md, .txt, .rst, .markdown)",
                    ErrorType.FILE_NOT_FOUND,
                    {"path": path, "attempted_extensions": [".md", ".txt", ".rst", ".markdown"]}
                )

            if not resolved_path.is_file():
                return ErrorHandler.create_error_result(
                    f"Path is not a file: {resolved_path}",
                    ErrorType.VALIDATION_ERROR,
                    {"path": str(resolved_path), "path_type": "directory" if resolved_path.is_dir() else "other"}
                )

            # Check file size before reading to prevent memory issues
            file_size = resolved_path.stat().st_size
            max_file_size = 50 * 1024 * 1024  # 50MB limit
            if file_size > max_file_size:
                return ErrorHandler.create_error_result(
                    f"File too large: {file_size} bytes (max: {max_file_size})",
                    ErrorType.RESOURCE_ERROR,
                    {"file_size": file_size, "max_size": max_file_size}
                )

            with open(resolved_path, 'r', encoding=encoding, errors='replace') as f:
                content = f.read()

            return ErrorHandler.create_success_result(
                content,
                {
                    "file_size": file_size,
                    "encoding": encoding,
                    "resolved_path": str(resolved_path)
                }
            )

        except Exception as e:
            return ErrorHandler.handle_exception(e, f"FileReadTool.execute(path={kwargs.get('path')})")

class FileWriteTool(Tool):
    """Tool for writing file contents."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="file_write",
            description="Write content to a file",
            category="File Operations",
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path to the file to write",
                    required=True
                ),
                ToolParameter(
                    name="content",
                    type="string",
                    description="Content to write to the file",
                    required=True
                ),
                ToolParameter(
                    name="encoding",
                    type="string",
                    description="File encoding (default: utf-8)",
                    required=False,
                    default="utf-8"
                ),
                ToolParameter(
                    name="create_dirs",
                    type="boolean",
                    description="Create parent directories if they don't exist",
                    required=False,
                    default=True
                )
            ]
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Write content to file."""
        try:
            path = kwargs.get('path')
            content = kwargs.get('content')
            encoding = kwargs.get('encoding', 'utf-8')
            create_dirs = kwargs.get('create_dirs', True)
            file_path = Path(path)

            if create_dirs:
                file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, 'w', encoding=encoding) as f:
                f.write(content)

            return ToolResult(
                success=True,
                output=f"Successfully wrote {len(content)} characters to {path}",
                metadata={"bytes_written": len(content.encode(encoding))}
            )

        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Failed to write file: {str(e)}"
            )

class FileListTool(Tool):
    """Tool for listing directory contents."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="file_list",
            description="List files and directories in a path",
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path to list (default: current directory)",
                    required=False,
                    default="."
                ),
                ToolParameter(
                    name="recursive",
                    type="boolean",
                    description="List files recursively",
                    required=False,
                    default=False
                ),
                ToolParameter(
                    name="include_hidden",
                    type="boolean",
                    description="Include hidden files (starting with .)",
                    required=False,
                    default=False
                ),
                ToolParameter(
                    name="extensions",
                    type="array",
                    description="Filter by file extensions (e.g., ['.py', '.js'])",
                    required=False
                )
            ]
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        """List directory contents."""
        try:
            path = kwargs.get('path', '.')
            recursive = kwargs.get('recursive', False)
            include_hidden = kwargs.get('include_hidden', False)
            extensions = kwargs.get('extensions')
            dir_path = Path(path)

            if not dir_path.exists():
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Path does not exist: {path}"
                )

            if not dir_path.is_dir():
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Path is not a directory: {path}"
                )

            files = []
            dirs = []

            if recursive:
                pattern = "**/*" if include_hidden else "**/[!.]*"
                for item in dir_path.glob(pattern):
                    if item.is_file():
                        if not extensions or item.suffix in extensions:
                            files.append(str(item.relative_to(dir_path)))
                    elif item.is_dir():
                        dirs.append(str(item.relative_to(dir_path)))
            else:
                for item in dir_path.iterdir():
                    if not include_hidden and item.name.startswith('.'):
                        continue

                    if item.is_file():
                        if not extensions or item.suffix in extensions:
                            files.append(item.name)
                    elif item.is_dir():
                        dirs.append(item.name + "/")

            # Sort results
            files.sort()
            dirs.sort()

            result_lines = []
            if dirs:
                result_lines.append("Directories:")
                result_lines.extend(f"  {d}" for d in dirs)

            if files:
                if dirs:
                    result_lines.append("")
                result_lines.append("Files:")
                result_lines.extend(f"  {f}" for f in files)

            if not dirs and not files:
                result_lines.append("(empty directory)")

            return ToolResult(
                success=True,
                output="\n".join(result_lines),
                metadata={
                    "file_count": len(files),
                    "dir_count": len(dirs),
                    "total_items": len(files) + len(dirs)
                }
            )

        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Failed to list directory: {str(e)}"
            )

class FileSearchTool(Tool):
    """Tool for searching file contents."""

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="file_search",
            description="Search for text patterns in files",
            parameters=[
                ToolParameter(
                    name="pattern",
                    type="string",
                    description="Text pattern to search for",
                    required=True
                ),
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path to search in (default: current directory)",
                    required=False,
                    default="."
                ),
                ToolParameter(
                    name="extensions",
                    type="array",
                    description="File extensions to search in",
                    required=False
                ),
                ToolParameter(
                    name="case_sensitive",
                    type="boolean",
                    description="Case sensitive search",
                    required=False,
                    default=False
                ),
                ToolParameter(
                    name="max_results",
                    type="number",
                    description="Maximum number of results to return",
                    required=False,
                    default=50
                )
            ]
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Search for pattern in files."""
        try:
            import re
            
            pattern = kwargs.get('pattern')
            path = kwargs.get('path', '.')
            extensions = kwargs.get('extensions')
            case_sensitive = kwargs.get('case_sensitive', False)
            max_results = kwargs.get('max_results', 50)
            search_path = Path(path)
            if not search_path.exists():
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Search path does not exist: {path}"
                )

            # Compile regex pattern
            flags = 0 if case_sensitive else re.IGNORECASE
            try:
                regex = re.compile(pattern, flags)
            except re.error as e:
                return ToolResult(
                    success=False,
                    output="",
                    error=f"Invalid regex pattern: {str(e)}"
                )

            results: List[Dict[str, Any]] = []
            files_searched = 0

            # Search files
            if search_path.is_file():
                files_to_search = [search_path]
            else:
                files_to_search = []
                for file_path in search_path.rglob("*"):
                    if file_path.is_file():
                        if extensions and file_path.suffix not in extensions:
                            continue
                        files_to_search.append(file_path)

            for file_path in files_to_search:
                if len(results) >= max_results:
                    break

                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()

                    files_searched += 1

                    # Find matches
                    for line_num, line in enumerate(content.split('\n'), 1):
                        if len(results) >= max_results:
                            break

                        matches = regex.finditer(line)
                        for match in matches:
                            results.append({
                                'file': str(file_path),
                                'line': line_num,
                                'text': line.strip(),
                                'match': match.group()
                            })

                            if len(results) >= max_results:
                                break

                except (UnicodeDecodeError, PermissionError):
                    # Skip files that can't be read
                    continue

            # Format results
            if not results:
                output = f"No matches found for pattern '{pattern}'"
            else:
                output_lines = [f"Found {len(results)} matches:"]
                for result in results:
                    output_lines.append(f"{result['file']}:{result['line']}: {result['text']}")
                output = "\n".join(output_lines)

            return ToolResult(
                success=True,
                output=output,
                metadata={
                    "matches": len(results),
                    "files_searched": files_searched,
                    "pattern": pattern
                }
            )

        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Search failed: {str(e)}"
            )
