"""
Code annotation and marking (sticker) system tool for OCode.
"""

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import Tool, ToolDefinition, ToolParameter, ToolResult


@dataclass
class CodeSticker:
    """Represents a code annotation/sticker."""

    id: str
    type: str  # "note", "todo", "fixme", "warning", "info", "bookmark", "question"
    file_path: str
    line_number: Optional[int] = None
    column_number: Optional[int] = None
    content: str = ""
    priority: str = "medium"  # "low", "medium", "high", "urgent"
    tags: Optional[List[str]] = None
    author: str = "ocode"
    created_at: str = ""
    updated_at: str = ""
    resolved: bool = False
    resolved_at: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at
        if self.tags is None:
            self.tags = []
        if self.context is None:
            self.context = {}


class StickerRequestTool(Tool):
    """Tool for creating and managing code annotations, notes, and markers."""

    def __init__(self):
        super().__init__()
        self.stickers: Dict[str, CodeSticker] = {}
        self._load_stickers()

    @property
    def definition(self) -> ToolDefinition:
        """Define the sticker tool specification.

        Returns:
            ToolDefinition with parameters for creating and managing code
            annotations including notes, TODOs, warnings, and bookmarks.
        """
        return ToolDefinition(
            name="sticker",
            description="Create, manage, and organize code annotations, notes, TODOs, and markers",  # noqa: E501
            parameters=[
                ToolParameter(
                    name="action",
                    type="string",
                    description="Action to perform: 'add', 'list', 'search', 'update', 'resolve', 'delete', 'export', 'import', 'stats'",  # noqa: E501
                    required=True,
                ),
                ToolParameter(
                    name="sticker_type",
                    type="string",
                    description="Type of sticker: 'note', 'todo', 'fixme', 'warning', 'info', 'bookmark', 'question'",  # noqa: E501
                    required=False,
                    default="note",
                ),
                ToolParameter(
                    name="file_path",
                    type="string",
                    description="Path to the file to annotate",
                    required=False,
                ),
                ToolParameter(
                    name="line_number",
                    type="number",
                    description="Line number in the file (1-based)",
                    required=False,
                ),
                ToolParameter(
                    name="column_number",
                    type="number",
                    description="Column number in the line (1-based)",
                    required=False,
                ),
                ToolParameter(
                    name="content",
                    type="string",
                    description="Content of the annotation/note",
                    required=False,
                ),
                ToolParameter(
                    name="priority",
                    type="string",
                    description="Priority level: 'low', 'medium', 'high', 'urgent'",
                    required=False,
                    default="medium",
                ),
                ToolParameter(
                    name="tags",
                    type="array",
                    description="Tags to categorize the sticker",
                    required=False,
                    default=[],
                ),
                ToolParameter(
                    name="sticker_id",
                    type="string",
                    description="ID of specific sticker to work with",
                    required=False,
                ),
                ToolParameter(
                    name="search_query",
                    type="string",
                    description="Search query for finding stickers",
                    required=False,
                ),
                ToolParameter(
                    name="filter_by",
                    type="object",
                    description="Filters for listing stickers (type, priority, tags, resolved, file)",  # noqa: E501
                    required=False,
                    default={},
                ),
                ToolParameter(
                    name="export_format",
                    type="string",
                    description="Export format: 'json', 'markdown', 'csv', 'html'",
                    required=False,
                    default="json",
                ),
            ],
        )

    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute sticker management actions."""
        try:
            # Extract parameters
            action = kwargs.get("action")
            sticker_type = kwargs.get("sticker_type", "note")
            file_path = kwargs.get("file_path")
            line_number = kwargs.get("line_number")
            column_number = kwargs.get("column_number")
            content = kwargs.get("content")
            priority = kwargs.get("priority", "medium")
            tags = kwargs.get("tags", [])
            sticker_id = kwargs.get("sticker_id")
            search_query = kwargs.get("search_query")
            filter_by = kwargs.get("filter_by", {})
            export_format = kwargs.get("export_format", "json")

            if not action:
                return ToolResult(
                    success=False, output="", error="action parameter is required"
                )

            if action == "add":
                return await self._add_sticker(
                    sticker_type,
                    file_path,
                    line_number,
                    column_number,
                    content,
                    priority,
                    tags,
                )
            elif action == "list":
                return await self._list_stickers(filter_by)
            elif action == "search":
                return await self._search_stickers(search_query, filter_by)
            elif action == "update":
                return await self._update_sticker(
                    sticker_id, sticker_type, content, priority, tags
                )
            elif action == "resolve":
                return await self._resolve_sticker(sticker_id)
            elif action == "delete":
                return await self._delete_sticker(sticker_id)
            elif action == "export":
                return await self._export_stickers(export_format, filter_by)
            elif action == "import":
                return await self._import_stickers(file_path)
            elif action == "stats":
                return await self._get_statistics(filter_by)
            else:
                return ToolResult(
                    success=False, output="", error=f"Unknown action: {action}"
                )

        except Exception as e:
            return ToolResult(
                success=False, output="", error=f"Sticker operation failed: {str(e)}"
            )

    async def _add_sticker(
        self,
        sticker_type: str,
        file_path: Optional[str],
        line_number: Optional[int],
        column_number: Optional[int],
        content: Optional[str],
        priority: str,
        tags: List[str],
    ) -> ToolResult:
        """Add a new code sticker/annotation."""
        if not content:
            return ToolResult(
                success=False,
                output="",
                error="content is required for adding a sticker",
            )

        if not file_path:
            file_path = "general"  # Allow general notes not tied to specific files

        # Validate sticker type
        valid_types = [
            "note",
            "todo",
            "fixme",
            "warning",
            "info",
            "bookmark",
            "question",
        ]
        if sticker_type not in valid_types:
            return ToolResult(
                success=False,
                output="",
                error=f"Invalid sticker type. Valid types: {', '.join(valid_types)}",
            )

        # Validate priority
        valid_priorities = ["low", "medium", "high", "urgent"]
        if priority not in valid_priorities:
            return ToolResult(
                success=False,
                output="",
                error=f"Invalid priority. Valid priorities: {', '.join(valid_priorities)}",  # noqa: E501
            )

        # Generate unique ID
        sticker_id = str(uuid.uuid4())[:8]

        # Create sticker
        sticker = CodeSticker(
            id=sticker_id,
            type=sticker_type,
            file_path=file_path,
            line_number=line_number,
            column_number=column_number,
            content=content,
            priority=priority,
            tags=tags,
        )

        # Add context if file exists
        if file_path != "general" and Path(file_path).exists():
            sticker.context = await self._extract_context(file_path, line_number)

        self.stickers[sticker_id] = sticker
        await self._save_stickers()

        output = f"Added {sticker_type} sticker (ID: {sticker_id})\n"
        output += f"File: {file_path}\n"
        if line_number:
            output += f"Line: {line_number}\n"
        if column_number:
            output += f"Column: {column_number}\n"
        output += f"Priority: {priority}\n"
        output += f"Content: {content}\n"
        if tags:
            output += f"Tags: {', '.join(tags)}\n"

        return ToolResult(
            success=True,
            output=output,
            metadata={"sticker_id": sticker_id, "sticker": asdict(sticker)},
        )

    async def _extract_context(
        self, file_path: str, line_number: Optional[int]
    ) -> Dict[str, Any]:
        """Extract context around a sticker location."""
        context: Dict[str, Any] = {"file_exists": False}

        try:
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                return context

            context["file_exists"] = True
            context["file_size"] = file_path_obj.stat().st_size
            context["file_extension"] = file_path_obj.suffix

            if line_number:
                with open(file_path_obj, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()

                context["total_lines"] = len(lines)

                if 1 <= line_number <= len(lines):
                    # Extract 2 lines before and after for context
                    start_line = max(1, line_number - 2)
                    end_line = min(len(lines), line_number + 2)

                    context["context_lines"] = {
                        "start": start_line,
                        "end": end_line,
                        "lines": {},
                    }

                    for i in range(start_line - 1, end_line):
                        context["context_lines"]["lines"][i + 1] = lines[i].rstrip()

                    context["target_line"] = lines[line_number - 1].rstrip()

        except Exception:  # nosec
            pass

        return context

    async def _list_stickers(self, filter_by: Dict[str, Any]) -> ToolResult:
        """List stickers with optional filtering."""
        filtered_stickers = self._filter_stickers(
            list(self.stickers.values()), filter_by
        )

        if not filtered_stickers:
            filter_desc = self._describe_filters(filter_by)
            return ToolResult(
                success=True,
                output=f"No stickers found{' matching ' + filter_desc if filter_desc else ''}.",  # noqa: E501
                metadata={"stickers": [], "count": 0},
            )

        # Sort by priority and date
        priority_order = {"urgent": 4, "high": 3, "medium": 2, "low": 1}
        filtered_stickers.sort(
            key=lambda s: (priority_order.get(s.priority, 0), s.created_at),
            reverse=True,
        )

        output = f"Code Stickers ({len(filtered_stickers)} found):\n"
        output += "=" * 50 + "\n"

        for sticker in filtered_stickers:
            output += f"ID: {sticker.id} [{sticker.type.upper()}]\n"
            output += f"File: {sticker.file_path}"
            if sticker.line_number:
                output += f":{sticker.line_number}"
            if sticker.column_number:
                output += f":{sticker.column_number}"
            output += "\n"

            output += f"Priority: {sticker.priority.upper()}\n"
            output += f"Content: {sticker.content}\n"

            if sticker.tags:
                output += f"Tags: {', '.join(sticker.tags)}\n"

            output += f"Created: {sticker.created_at}\n"

            if sticker.resolved:
                output += f"✅ RESOLVED ({sticker.resolved_at})\n"

            output += "-" * 30 + "\n"

        return ToolResult(
            success=True,
            output=output,
            metadata={
                "stickers": [asdict(s) for s in filtered_stickers],
                "count": len(filtered_stickers),
            },
        )

    def _filter_stickers(
        self, stickers: List[CodeSticker], filter_by: Dict[str, Any]
    ) -> List[CodeSticker]:
        """Apply filters to sticker list."""
        filtered = stickers

        if "type" in filter_by:
            filtered = [s for s in filtered if s.type == filter_by["type"]]

        if "priority" in filter_by:
            filtered = [s for s in filtered if s.priority == filter_by["priority"]]

        if "resolved" in filter_by:
            filtered = [s for s in filtered if s.resolved == filter_by["resolved"]]

        if "file" in filter_by:
            filtered = [s for s in filtered if filter_by["file"] in s.file_path]

        if "tags" in filter_by:
            required_tags = (
                filter_by["tags"]
                if isinstance(filter_by["tags"], list)
                else [filter_by["tags"]]
            )
            filtered = [
                s
                for s in filtered
                if s.tags and any(tag in s.tags for tag in required_tags)
            ]

        if "author" in filter_by:
            filtered = [s for s in filtered if s.author == filter_by["author"]]

        return filtered

    def _describe_filters(self, filter_by: Dict[str, Any]) -> str:
        """Create human-readable description of filters."""
        filters = []

        if "type" in filter_by:
            filters.append(f"type={filter_by['type']}")
        if "priority" in filter_by:
            filters.append(f"priority={filter_by['priority']}")
        if "resolved" in filter_by:
            filters.append(f"resolved={filter_by['resolved']}")
        if "file" in filter_by:
            filters.append(f"file contains '{filter_by['file']}'")
        if "tags" in filter_by:
            tags = (
                filter_by["tags"]
                if isinstance(filter_by["tags"], list)
                else [filter_by["tags"]]
            )
            filters.append(f"tags include {', '.join(tags)}")

        return " and ".join(filters) if filters else ""

    async def _search_stickers(
        self, search_query: Optional[str], filter_by: Dict[str, Any]
    ) -> ToolResult:
        """Search stickers by content and other criteria."""
        if not search_query:
            return ToolResult(
                success=False,
                output="",
                error="search_query is required for searching stickers",
            )

        # Start with all stickers and apply filters
        all_stickers = list(self.stickers.values())
        filtered_stickers = self._filter_stickers(all_stickers, filter_by)

        # Search within filtered results
        query_lower = search_query.lower()
        matching_stickers = []

        for sticker in filtered_stickers:
            # Search in content, file path, and tags
            if (
                query_lower in sticker.content.lower()
                or query_lower in sticker.file_path.lower()
                or (
                    sticker.tags
                    and any(query_lower in tag.lower() for tag in sticker.tags)
                )
            ):
                matching_stickers.append(sticker)

        if not matching_stickers:
            return ToolResult(
                success=True,
                output=f"No stickers found matching '{search_query}'.",
                metadata={"stickers": [], "count": 0, "query": search_query},
            )

        # Sort by relevance (simple scoring)
        def relevance_score(sticker: CodeSticker) -> int:
            score = 0
            if query_lower in sticker.content.lower():
                score += 10
            if query_lower in sticker.file_path.lower():
                score += 5
            if sticker.tags:
                for tag in sticker.tags:
                    if query_lower in tag.lower():
                        score += 3
            return score

        matching_stickers.sort(key=relevance_score, reverse=True)

        output = (
            f"Search Results for '{search_query}' ({len(matching_stickers)} found):\n"
        )
        output += "=" * 60 + "\n"

        for sticker in matching_stickers:
            output += f"ID: {sticker.id} [{sticker.type.upper()}] - {sticker.priority.upper()}\n"  # noqa: E501
            output += f"File: {sticker.file_path}"
            if sticker.line_number:
                output += f":{sticker.line_number}"
            output += "\n"
            output += f"Content: {sticker.content}\n"

            if sticker.tags:
                output += f"Tags: {', '.join(sticker.tags)}\n"

            if sticker.resolved:
                output += "✅ RESOLVED\n"

            output += "-" * 40 + "\n"

        return ToolResult(
            success=True,
            output=output,
            metadata={
                "stickers": [asdict(s) for s in matching_stickers],
                "count": len(matching_stickers),
                "query": search_query,
            },
        )

    async def _update_sticker(
        self,
        sticker_id: Optional[str],
        sticker_type: str,
        content: Optional[str],
        priority: str,
        tags: List[str],
    ) -> ToolResult:
        """Update an existing sticker."""
        if not sticker_id:
            return ToolResult(
                success=False, output="", error="sticker_id is required for updating"
            )

        if sticker_id not in self.stickers:
            return ToolResult(
                success=False,
                output="",
                error=f"Sticker with ID {sticker_id} not found",
            )

        sticker = self.stickers[sticker_id]
        old_content = sticker.content

        # Update fields if provided
        if content:
            sticker.content = content
        if sticker_type != "note":  # Only update if different from default
            sticker.type = sticker_type
        if priority != "medium":  # Only update if different from default
            sticker.priority = priority
        if tags:
            sticker.tags = tags

        sticker.updated_at = datetime.now().isoformat()

        await self._save_stickers()

        output = f"Updated sticker (ID: {sticker_id})\n"
        if content and content != old_content:
            output += f"Content: {old_content} → {content}\n"
        output += f"Type: {sticker.type}\n"
        output += f"Priority: {sticker.priority}\n"
        if tags:
            output += f"Tags: {', '.join(tags)}\n"
        output += f"Updated: {sticker.updated_at}\n"

        return ToolResult(
            success=True,
            output=output,
            metadata={"sticker_id": sticker_id, "sticker": asdict(sticker)},
        )

    async def _resolve_sticker(self, sticker_id: Optional[str]) -> ToolResult:
        """Mark a sticker as resolved."""
        if not sticker_id:
            return ToolResult(
                success=False, output="", error="sticker_id is required for resolving"
            )

        if sticker_id not in self.stickers:
            return ToolResult(
                success=False,
                output="",
                error=f"Sticker with ID {sticker_id} not found",
            )

        sticker = self.stickers[sticker_id]

        if sticker.resolved:
            return ToolResult(
                success=False,
                output="",
                error=f"Sticker {sticker_id} is already resolved",
            )

        sticker.resolved = True
        sticker.resolved_at = datetime.now().isoformat()
        sticker.updated_at = sticker.resolved_at

        await self._save_stickers()

        output = f"✅ Resolved sticker (ID: {sticker_id})\n"
        output += f"Type: {sticker.type}\n"
        output += f"Content: {sticker.content}\n"
        output += f"Resolved at: {sticker.resolved_at}\n"

        return ToolResult(
            success=True,
            output=output,
            metadata={"sticker_id": sticker_id, "sticker": asdict(sticker)},
        )

    async def _delete_sticker(self, sticker_id: Optional[str]) -> ToolResult:
        """Delete a sticker."""
        if not sticker_id:
            return ToolResult(
                success=False, output="", error="sticker_id is required for deletion"
            )

        if sticker_id not in self.stickers:
            return ToolResult(
                success=False,
                output="",
                error=f"Sticker with ID {sticker_id} not found",
            )

        sticker = self.stickers[sticker_id]
        del self.stickers[sticker_id]

        await self._save_stickers()

        output = f"Deleted sticker (ID: {sticker_id})\n"
        output += f"Type: {sticker.type}\n"
        output += f"Content: {sticker.content}\n"

        return ToolResult(
            success=True, output=output, metadata={"deleted_sticker": asdict(sticker)}
        )

    async def _export_stickers(
        self, export_format: str, filter_by: Dict[str, Any]
    ) -> ToolResult:
        """Export stickers in various formats."""
        all_stickers = list(self.stickers.values())
        filtered_stickers = self._filter_stickers(all_stickers, filter_by)

        if export_format == "json":
            exported_data = json.dumps([asdict(s) for s in filtered_stickers], indent=2)
        elif export_format == "markdown":
            exported_data = self._export_as_markdown(filtered_stickers)
        elif export_format == "csv":
            exported_data = self._export_as_csv(filtered_stickers)
        elif export_format == "html":
            exported_data = self._export_as_html(filtered_stickers)
        else:
            return ToolResult(
                success=False,
                output="",
                error=f"Unsupported export format: {export_format}",
            )

        # Save to file
        export_filename = f"stickers_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{export_format}"  # noqa: E501
        export_path = Path.cwd() / ".ocode" / "exports"
        export_path.mkdir(parents=True, exist_ok=True)

        full_path = export_path / export_filename
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(exported_data)

        output = f"Exported {len(filtered_stickers)} stickers to {full_path}\n"
        output += f"Format: {export_format.upper()}\n"

        return ToolResult(
            success=True,
            output=output,
            metadata={
                "export_path": str(full_path),
                "format": export_format,
                "count": len(filtered_stickers),
            },
        )

    def _export_as_markdown(self, stickers: List[CodeSticker]) -> str:
        """Export stickers as markdown."""
        md = "# Code Stickers Export\n\n"
        md += f"Generated: {datetime.now().isoformat()}\n"
        md += f"Total stickers: {len(stickers)}\n\n"

        # Group by type
        by_type: Dict[str, List[CodeSticker]] = {}
        for sticker in stickers:
            if sticker.type not in by_type:
                by_type[sticker.type] = []
            by_type[sticker.type].append(sticker)

        for sticker_type, type_stickers in by_type.items():
            md += f"## {sticker_type.upper()} ({len(type_stickers)})\n\n"

            for sticker in type_stickers:
                md += f"### {sticker.id}\n\n"
                md += f"**File:** {sticker.file_path}"
                if sticker.line_number:
                    md += f":{sticker.line_number}"
                md += "\n\n"
                md += f"**Priority:** {sticker.priority}\n\n"
                md += f"**Content:** {sticker.content}\n\n"

                if sticker.tags:
                    md += f"**Tags:** {', '.join(sticker.tags)}\n\n"

                md += f"**Created:** {sticker.created_at}\n\n"

                if sticker.resolved:
                    md += f"**Status:** ✅ RESOLVED ({sticker.resolved_at})\n\n"

                md += "---\n\n"

        return md

    def _export_as_csv(self, stickers: List[CodeSticker]) -> str:
        """Export stickers as CSV."""
        import csv
        import io

        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow(
            [
                "ID",
                "Type",
                "File",
                "Line",
                "Column",
                "Content",
                "Priority",
                "Tags",
                "Author",
                "Created",
                "Updated",
                "Resolved",
                "Resolved At",
            ]
        )

        # Data
        for sticker in stickers:
            writer.writerow(
                [
                    sticker.id,
                    sticker.type,
                    sticker.file_path,
                    sticker.line_number or "",
                    sticker.column_number or "",
                    sticker.content,
                    sticker.priority,
                    ";".join(sticker.tags) if sticker.tags else "",
                    sticker.author,
                    sticker.created_at,
                    sticker.updated_at,
                    sticker.resolved,
                    sticker.resolved_at or "",
                ]
            )

        return output.getvalue()

    def _export_as_html(self, stickers: List[CodeSticker]) -> str:
        """Export stickers as HTML."""
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Code Stickers Export</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .sticker {{ border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 5px; }}  # noqa: E501
        .sticker-header {{ font-weight: bold; color: #333; }}
        .priority-high {{ border-left: 5px solid #ff4444; }}
        .priority-urgent {{ border-left: 5px solid #ff0000; }}
        .priority-medium {{ border-left: 5px solid #ffaa00; }}
        .priority-low {{ border-left: 5px solid #44ff44; }}
        .resolved {{ background-color: #f0fff0; }}
        .tags {{ color: #666; font-size: 0.9em; }}
    </style>
</head>
<body>
    <h1>Code Stickers Export</h1>
    <p>Generated: {datetime.now().isoformat()}</p>
    <p>Total stickers: {len(stickers)}</p>
"""

        for sticker in stickers:
            resolved_class = " resolved" if sticker.resolved else ""
            priority_class = f" priority-{sticker.priority}"

            html += f"""
    <div class="sticker{priority_class}{resolved_class}">
        <div class="sticker-header">{sticker.id} [{sticker.type.upper()}]</div>
        <p><strong>File:</strong> {sticker.file_path}"""

            if sticker.line_number:
                html += f":{sticker.line_number}"

            html += f"""</p>
        <p><strong>Priority:</strong> {sticker.priority}</p>
        <p><strong>Content:</strong> {sticker.content}</p>"""

            if sticker.tags:
                html += f'<p class="tags"><strong>Tags:</strong> {", ".join(sticker.tags)}</p>'  # noqa: E501

            html += f"""<p><strong>Created:</strong> {sticker.created_at}</p>"""

            if sticker.resolved:
                html += f"<p><strong>Status:</strong> ✅ RESOLVED ({sticker.resolved_at})</p>"  # noqa: E501

            html += "    </div>"

        html += """
</body>
</html>"""

        return html

    async def _import_stickers(self, file_path: Optional[str]) -> ToolResult:
        """Import stickers from a file."""
        if not file_path:
            return ToolResult(
                success=False,
                output="",
                error="file_path is required for importing stickers",
            )

        import_path = Path(file_path)
        if not import_path.exists():
            return ToolResult(
                success=False, output="", error=f"Import file not found: {file_path}"
            )

        try:
            with open(import_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            imported_count = 0
            for item in data:
                # Create sticker from imported data
                sticker = CodeSticker(**item)
                # Generate new ID to avoid conflicts
                sticker.id = str(uuid.uuid4())[:8]
                self.stickers[sticker.id] = sticker
                imported_count += 1

            await self._save_stickers()

            output = (
                f"Successfully imported {imported_count} stickers from {file_path}\n"
            )

            return ToolResult(
                success=True,
                output=output,
                metadata={"imported_count": imported_count, "source_file": file_path},
            )

        except Exception as e:
            return ToolResult(
                success=False, output="", error=f"Failed to import stickers: {str(e)}"
            )

    async def _get_statistics(self, filter_by: Dict[str, Any]) -> ToolResult:
        """Get statistics about stickers."""
        all_stickers = list(self.stickers.values())
        filtered_stickers = self._filter_stickers(all_stickers, filter_by)

        if not filtered_stickers:
            return ToolResult(
                success=True,
                output="No stickers found for statistics.",
                metadata={"statistics": {}},
            )

        # Calculate statistics
        stats = {
            "total": len(filtered_stickers),
            "by_type": {},
            "by_priority": {},
            "by_status": {"resolved": 0, "open": 0},
            "by_file": {},
            "by_author": {},
            "tags": {},
        }

        for sticker in filtered_stickers:
            # By type
            by_type = stats["by_type"]
            if isinstance(by_type, dict):
                by_type[sticker.type] = by_type.get(sticker.type, 0) + 1

            # By priority
            by_priority = stats["by_priority"]
            if isinstance(by_priority, dict):
                by_priority[sticker.priority] = by_priority.get(sticker.priority, 0) + 1

            # By status
            by_status = stats["by_status"]
            if isinstance(by_status, dict):
                if sticker.resolved:
                    by_status["resolved"] += 1
                else:
                    by_status["open"] += 1

            # By file
            by_file = stats["by_file"]
            if isinstance(by_file, dict):
                by_file[sticker.file_path] = by_file.get(sticker.file_path, 0) + 1

            # By author
            by_author = stats["by_author"]
            if isinstance(by_author, dict):
                by_author[sticker.author] = by_author.get(sticker.author, 0) + 1

            # Tags
            if sticker.tags:
                tags_stats = stats["tags"]
                if isinstance(tags_stats, dict):
                    for tag in sticker.tags:
                        tags_stats[tag] = tags_stats.get(tag, 0) + 1

        # Generate output
        output = "Sticker Statistics:\n"
        output += "=" * 30 + "\n"
        output += f"Total stickers: {stats['total']}\n\n"

        output += "By Type:\n"
        by_type_stats = stats["by_type"]
        if isinstance(by_type_stats, dict):
            for stype, count in sorted(by_type_stats.items()):
                output += f"  {stype}: {count}\n"

        output += "\nBy Priority:\n"
        priority_order = ["urgent", "high", "medium", "low"]
        for priority in priority_order:
            by_priority_stats = stats["by_priority"]
            if isinstance(by_priority_stats, dict) and priority in by_priority_stats:
                output += f"  {priority}: {by_priority_stats[priority]}\n"

        output += "\nStatus:\n"
        by_status_stats = stats["by_status"]
        if isinstance(by_status_stats, dict):
            output += f"  Open: {by_status_stats.get('open', 0)}\n"
            output += f"  Resolved: {by_status_stats.get('resolved', 0)}\n"

        tags_stats = stats["tags"]
        if isinstance(tags_stats, dict) and tags_stats:
            output += "\nTop Tags:\n"
            top_tags = sorted(tags_stats.items(), key=lambda x: x[1], reverse=True)[:5]
            for tag, count in top_tags:
                output += f"  {tag}: {count}\n"

        return ToolResult(success=True, output=output, metadata={"statistics": stats})

    def _get_stickers_file(self) -> Path:
        """Get the path to the stickers storage file."""
        stickers_dir = Path.cwd() / ".ocode" / "stickers"
        stickers_dir.mkdir(parents=True, exist_ok=True)
        return stickers_dir / "stickers.json"

    def _load_stickers(self) -> None:
        """Load stickers from storage file."""
        stickers_file = self._get_stickers_file()

        if stickers_file.exists():
            try:
                with open(stickers_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                for sticker_data in data:
                    sticker = CodeSticker(**sticker_data)
                    self.stickers[sticker.id] = sticker

            except Exception:
                # If loading fails, start with empty stickers
                self.stickers = {}

    async def _save_stickers(self) -> None:
        """Save stickers to storage file."""
        stickers_file = self._get_stickers_file()

        try:
            sticker_data = [asdict(sticker) for sticker in self.stickers.values()]

            with open(stickers_file, "w", encoding="utf-8") as f:
                json.dump(sticker_data, f, indent=2)

        except Exception:  # nosec
            # Silently fail if save doesn't work
            pass
