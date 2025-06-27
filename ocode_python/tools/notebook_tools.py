"""
Jupyter notebook tools for OCode.
"""

import json
import os  # noqa: F401
import shutil
from typing import Any, Dict, List

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

# File size limit for notebook files (50MB)
MAX_NOTEBOOK_SIZE_BYTES = 50 * 1024 * 1024


class NotebookReadTool(Tool):
    """Tool for reading and analyzing Jupyter notebook files."""

    @property
    def definition(self) -> ToolDefinition:
        """Define the notebook_read tool specification.

        Returns:
            ToolDefinition with parameters for reading Jupyter notebooks
            including cells, outputs, metadata, and filtering options.
        """
        return ToolDefinition(
            name="notebook_read",
            description="Read and analyze Jupyter notebook files (.ipynb), extracting cells, outputs, and metadata",  # noqa: E501
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path to the notebook file",
                    required=True,
                ),
                ToolParameter(
                    name="include_outputs",
                    type="boolean",
                    description="Include cell outputs in the result",
                    required=False,
                    default=True,
                ),
                ToolParameter(
                    name="include_metadata",
                    type="boolean",
                    description="Include notebook and cell metadata",
                    required=False,
                    default=False,
                ),
                ToolParameter(
                    name="cell_types",
                    type="array",
                    description="Filter by cell types (code, markdown, raw)",
                    required=False,
                    default=None,
                ),
                ToolParameter(
                    name="cell_range",
                    type="string",
                    description="Cell range to read (e.g., '1 - 5' or '3,5,7')",
                    required=False,
                    default=None,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Read and analyze a Jupyter notebook file."""
        try:
            # Validate required parameters
            validation_error = ErrorHandler.validate_required_params(kwargs, ["path"])
            if validation_error:
                return validation_error

            # Extract parameters
            path = kwargs.get("path")
            include_outputs = kwargs.get("include_outputs", True)
            include_metadata = kwargs.get("include_metadata", False)
            cell_types = kwargs.get("cell_types")
            cell_range = kwargs.get("cell_range")

            # Validate path
            if not isinstance(path, str):
                return ErrorHandler.create_error_result(
                    "Path parameter must be a string", ErrorType.VALIDATION_ERROR
                )
            is_valid, error_msg, normalized_path = path_validator.validate_path(
                path, check_exists=True
            )
            if not is_valid or normalized_path is None:
                return ErrorHandler.create_error_result(
                    f"Invalid path: {error_msg}", ErrorType.VALIDATION_ERROR
                )

            # At this point normalized_path is guaranteed to be non-None
            assert normalized_path is not None  # Type safety for MyPy
            # Use validated path
            notebook_path = normalized_path

            # Check if it's a notebook file
            if notebook_path.suffix.lower() != ".ipynb":
                return ErrorHandler.create_error_result(
                    f"File is not a Jupyter notebook (.ipynb): {path}",
                    ErrorType.VALIDATION_ERROR,
                )

            # Check file size (limit to 50MB for safety)
            file_size = notebook_path.stat().st_size
            if file_size > MAX_NOTEBOOK_SIZE_BYTES:
                return ErrorHandler.create_error_result(
                    f"Notebook file too large: "
                    f"{file_size / (1024*1024):.1f}MB (max 50MB)",
                    ErrorType.RESOURCE_ERROR,
                )

            # Read and parse notebook with timeout and proper resource management
            try:
                async with async_timeout(30):  # 30 second timeout for large notebooks
                    with open(notebook_path, "r", encoding="utf-8") as f:
                        notebook_data = json.load(f)
            except UnicodeDecodeError as e:
                return ErrorHandler.create_error_result(
                    f"Encoding error reading notebook: {str(e)}",
                    ErrorType.VALIDATION_ERROR,
                )

            # Extract basic info
            result = {
                "file": str(notebook_path),
                "format": notebook_data.get("nbformat", "unknown"),
                "kernel": notebook_data.get("metadata", {})
                .get("kernelspec", {})
                .get("name", "unknown"),
                "language": notebook_data.get("metadata", {})
                .get("language_info", {})
                .get("name", "unknown"),
                "cells": [],
            }

            # Add notebook metadata if requested
            if include_metadata:
                result["notebook_metadata"] = notebook_data.get("metadata", {})

            # Parse cell range if provided
            selected_indices = None
            if cell_range:
                selected_indices = self._parse_cell_range(
                    cell_range, len(notebook_data.get("cells", []))
                )

            # Process cells
            cells = notebook_data.get("cells", [])
            for i, cell in enumerate(cells):
                # Check if cell index is in selected range
                if selected_indices is not None and i not in selected_indices:
                    continue

                cell_type = cell.get("cell_type", "unknown")

                # Filter by cell type if specified
                if cell_types and cell_type not in cell_types:
                    continue

                cell_info = {
                    "index": i,
                    "type": cell_type,
                    "source": "".join(cell.get("source", [])),
                    "execution_count": cell.get("execution_count"),
                }

                # Add outputs for code cells if requested
                if include_outputs and cell_type == "code" and "outputs" in cell:
                    cell_info["outputs"] = self._extract_outputs(cell["outputs"])

                # Add cell metadata if requested
                if include_metadata:
                    cell_info["metadata"] = cell.get("metadata", {})

                result["cells"].append(cell_info)

            # Generate summary
            total_cells = len(cells)
            code_cells = len([c for c in cells if c.get("cell_type") == "code"])
            markdown_cells = len([c for c in cells if c.get("cell_type") == "markdown"])

            summary = f"Notebook: {notebook_path.name}\n"
            summary += f"Total cells: {total_cells} (Code: {code_cells}, Markdown: {markdown_cells})\n"  # noqa: E501
            summary += f"Kernel: {result['kernel']}, Language: {result['language']}\n\n"

            # Add cells to output
            for cell in result["cells"]:
                summary += f"Cell [{cell['index']}] ({cell['type']})\n"
                if cell["type"] == "code" and cell["execution_count"]:
                    summary += f"Execution count: {cell['execution_count']}\n"
                summary += f"Source:\n{cell['source']}\n"

                if include_outputs and "outputs" in cell and cell["outputs"]:
                    summary += "Outputs:\n"
                    for output in cell["outputs"]:
                        summary += f"  {output}\n"
                summary += "\n" + "-" * 50 + "\n"

            return ErrorHandler.create_success_result(summary, metadata=result)

        except json.JSONDecodeError as e:
            return ErrorHandler.create_error_result(
                f"Invalid JSON in notebook file: {str(e)}", ErrorType.VALIDATION_ERROR
            )
        except Exception as e:
            return ErrorHandler.handle_exception(e, "notebook_read")

    def _parse_cell_range(self, cell_range: str, total_cells: int) -> List[int]:
        """Parse cell range string into list of indices."""
        indices: List[int] = []

        for part in cell_range.split(","):
            part = part.strip()
            if "-" in part:
                # Range like "1 - 5"
                start, end = part.split("-")
                start_idx = max(0, int(start.strip()) - 1)  # Convert to 0-based
                end_idx = min(total_cells, int(end.strip()))  # Inclusive
                indices.extend(range(start_idx, end_idx))
            else:
                # Single cell like "3"
                idx = int(part.strip()) - 1  # Convert to 0-based
                if 0 <= idx < total_cells:
                    indices.append(idx)

        return sorted(list(set(indices)))  # Remove duplicates and sort

    def _extract_outputs(self, outputs: List[Dict[str, Any]]) -> List[str]:
        """Extract readable output from notebook cell outputs."""
        result = []

        for output in outputs:
            output_type = output.get("output_type", "")

            if output_type == "stream":
                # stdout/stderr output
                text = "".join(output.get("text", []))
                result.append(f"[{output.get('name', 'stream')}] {text.strip()}")

            elif output_type == "execute_result":
                # Return value output
                data = output.get("data", {})
                if "text/plain" in data:
                    text = "".join(data["text/plain"])
                    result.append(f"[result] {text.strip()}")

            elif output_type == "display_data":
                # Display output (plots, images, etc.)
                data = output.get("data", {})
                if "text/plain" in data:
                    text = "".join(data["text/plain"])
                    result.append(f"[display] {text.strip()}")
                elif "image/png" in data:
                    result.append("[display] <PNG image>")
                elif "text/html" in data:
                    result.append("[display] <HTML content>")

            elif output_type == "error":
                # Error output
                ename = output.get("ename", "Error")
                evalue = output.get("evalue", "")
                result.append(f"[error] {ename}: {evalue}")

        return result


class NotebookEditTool(Tool):
    """Tool for editing Jupyter notebook files."""

    @property
    def definition(self) -> ToolDefinition:
        """Define the notebook_edit tool specification.

        Returns:
            ToolDefinition with parameters for editing Jupyter notebooks
            including add, edit, delete, and clear operations on cells.
        """
        return ToolDefinition(
            name="notebook_edit",
            description="Edit Jupyter notebook files by modifying, adding, or removing cells",  # noqa: E501
            parameters=[
                ToolParameter(
                    name="path",
                    type="string",
                    description="Path to the notebook file",
                    required=True,
                ),
                ToolParameter(
                    name="operation",
                    type="string",
                    description="Operation to perform: 'update_cell', 'add_cell', 'remove_cell', 'clear_outputs', 'set_metadata'",  # noqa: E501
                    required=True,
                ),
                ToolParameter(
                    name="cell_index",
                    type="number",
                    description="Index of the cell to modify (0-based)",
                    required=False,
                ),
                ToolParameter(
                    name="cell_type",
                    type="string",
                    description="Type of cell: 'code', 'markdown', or 'raw'",
                    required=False,
                    default="code",
                ),
                ToolParameter(
                    name="source",
                    type="string",
                    description="New source code/content for the cell",
                    required=False,
                ),
                ToolParameter(
                    name="metadata",
                    type="object",
                    description="Metadata to set (for set_metadata operation)",
                    required=False,
                ),
                ToolParameter(
                    name="backup",
                    type="boolean",
                    description="Create backup before editing",
                    required=False,
                    default=True,
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Edit a Jupyter notebook file."""
        try:
            # Validate required parameters
            validation_error = ErrorHandler.validate_required_params(
                kwargs, ["path", "operation"]
            )
            if validation_error:
                return validation_error

            # Extract parameters
            path = kwargs.get("path")
            operation = kwargs.get("operation")
            cell_index = kwargs.get("cell_index")
            cell_type = kwargs.get("cell_type", "code")
            source = kwargs.get("source")
            metadata = kwargs.get("metadata")
            backup = kwargs.get("backup", True)

            # Validate path
            if not isinstance(path, str):
                return ErrorHandler.create_error_result(
                    "Path parameter must be a string", ErrorType.VALIDATION_ERROR
                )
            is_valid, error_msg, normalized_path = path_validator.validate_path(
                path, check_exists=True
            )
            if not is_valid or normalized_path is None:
                return ErrorHandler.create_error_result(
                    f"Invalid path: {error_msg}", ErrorType.VALIDATION_ERROR
                )

            # At this point normalized_path is guaranteed to be non-None
            assert normalized_path is not None  # Type safety for MyPy
            # Use validated path
            notebook_path = normalized_path

            # Create backup if requested
            backup_path = None
            if backup:
                backup_path = notebook_path.with_suffix(f"{notebook_path.suffix}.bak")

                shutil.copy2(notebook_path, backup_path)

            # Read current notebook with timeout
            try:
                async with async_timeout(30):  # 30 second timeout
                    with open(notebook_path, "r", encoding="utf-8") as f:
                        notebook_data = json.load(f)
            except UnicodeDecodeError as e:
                return ErrorHandler.create_error_result(
                    f"Encoding error reading notebook: {str(e)}",
                    ErrorType.VALIDATION_ERROR,
                )

            cells = notebook_data.get("cells", [])
            result_message = ""

            # Perform the requested operation
            if operation == "update_cell":
                if cell_index is None or source is None:
                    return ErrorHandler.create_error_result(
                        "update_cell requires cell_index and source parameters",
                        ErrorType.VALIDATION_ERROR,
                    )

                if not (0 <= cell_index < len(cells)):
                    return ErrorHandler.create_error_result(
                        f"Invalid cell index: {cell_index}. "
                        f"Notebook has {len(cells)} cells.",
                        ErrorType.VALIDATION_ERROR,
                    )

                cells[cell_index]["source"] = source.split("\n")
                cells[cell_index]["cell_type"] = cell_type
                result_message = f"Updated cell {cell_index}"

            elif operation == "add_cell":
                if source is None:
                    return ErrorHandler.create_error_result(
                        "add_cell requires source parameter", ErrorType.VALIDATION_ERROR
                    )

                new_cell = {
                    "cell_type": cell_type,
                    "source": source.split("\n"),
                    "metadata": {},
                }

                if cell_type == "code":
                    new_cell["execution_count"] = None
                    new_cell["outputs"] = []

                if cell_index is None:
                    # Add at the end
                    cells.append(new_cell)
                    result_message = f"Added new {cell_type} cell at the end"
                else:
                    # Insert at specific position
                    if not (0 <= cell_index <= len(cells)):
                        return ErrorHandler.create_error_result(
                            f"Invalid cell index: {cell_index}. "
                            f"Valid range: 0-{len(cells)}",
                            ErrorType.VALIDATION_ERROR,
                        )
                    cells.insert(cell_index, new_cell)
                    result_message = f"Added new {cell_type} cell at index {cell_index}"

            elif operation == "remove_cell":
                if cell_index is None:
                    return ErrorHandler.create_error_result(
                        "remove_cell requires cell_index parameter",
                        ErrorType.VALIDATION_ERROR,
                    )

                if not (0 <= cell_index < len(cells)):
                    return ErrorHandler.create_error_result(
                        f"Invalid cell index: {cell_index}. "
                        f"Notebook has {len(cells)} cells.",
                        ErrorType.VALIDATION_ERROR,
                    )

                removed_cell = cells.pop(cell_index)
                result_message = f"Removed {removed_cell.get('cell_type', 'unknown')} cell at index {cell_index}"  # noqa: E501

            elif operation == "clear_outputs":
                cleared_count = 0
                for cell in cells:
                    if cell.get("cell_type") == "code":
                        cell["outputs"] = []
                        cell["execution_count"] = None
                        cleared_count += 1
                result_message = f"Cleared outputs from {cleared_count} code cells"

            elif operation == "set_metadata":
                if metadata is None:
                    return ErrorHandler.create_error_result(
                        "set_metadata requires metadata parameter",
                        ErrorType.VALIDATION_ERROR,
                    )

                if cell_index is not None:
                    # Set metadata for specific cell
                    if not (0 <= cell_index < len(cells)):
                        return ErrorHandler.create_error_result(
                            f"Invalid cell index: {cell_index}. "
                            f"Notebook has {len(cells)} cells.",
                            ErrorType.VALIDATION_ERROR,
                        )
                    cells[cell_index]["metadata"].update(metadata)
                    result_message = f"Updated metadata for cell {cell_index}"
                else:
                    # Set notebook-level metadata
                    notebook_data.setdefault("metadata", {}).update(metadata)
                    result_message = "Updated notebook metadata"

            else:
                return ErrorHandler.create_error_result(
                    f"Unknown operation: {operation}", ErrorType.VALIDATION_ERROR
                )

            # Update cells in notebook data
            notebook_data["cells"] = cells

            # Write back to file with proper error handling
            try:
                with open(notebook_path, "w", encoding="utf-8") as f:
                    json.dump(notebook_data, f, indent=2, ensure_ascii=False)
            except OSError as e:
                return ErrorHandler.create_error_result(
                    f"Failed to write notebook file: {str(e)}", ErrorType.RESOURCE_ERROR
                )

            return ErrorHandler.create_success_result(
                f"Successfully edited notebook: {result_message}",
                metadata={
                    "operation": operation,
                    "cell_count": len(cells),
                    "backup_created": backup,
                    "backup_path": str(backup_path) if backup else None,
                },
            )

        except json.JSONDecodeError as e:
            return ErrorHandler.create_error_result(
                f"Invalid JSON in notebook file: {str(e)}", ErrorType.VALIDATION_ERROR
            )
        except Exception as e:
            return ErrorHandler.handle_exception(e, "notebook_edit")
