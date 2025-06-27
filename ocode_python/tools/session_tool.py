"""
Session and checkpoint management tool for interactive conversation control.
"""

import json
import time
from typing import Any, Dict, List, Optional

from ..core.checkpoint import CheckpointManager
from ..core.session import SessionManager, export_session_to_markdown
from .base import Tool, ToolDefinition, ToolResult


class SessionTool(Tool):
    """Tool for managing conversation sessions and checkpoints."""

    def __init__(self):
        super().__init__()
        self.session_manager = SessionManager()
        self.checkpoint_manager = CheckpointManager()

    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="session_manager",
            description="Manage conversation sessions and checkpoints - save, load, resume, and branch conversations",
            parameters={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": [
                            "list_sessions",
                            "save_session",
                            "load_session",
                            "delete_session",
                            "export_session",
                            "create_checkpoint",
                            "list_checkpoints",
                            "resume_checkpoint",
                            "branch_checkpoint",
                            "delete_checkpoint",
                            "cleanup_old"
                        ],
                        "description": "The session management action to perform"
                    },
                    "session_id": {
                        "type": "string",
                        "description": "Session ID for load/delete/export operations"
                    },
                    "checkpoint_id": {
                        "type": "string",
                        "description": "Checkpoint ID for checkpoint operations"
                    },
                    "description": {
                        "type": "string",
                        "description": "Description for checkpoints or sessions"
                    },
                    "tags": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tags for categorizing checkpoints"
                    },
                    "output_file": {
                        "type": "string",
                        "description": "Output file path for exports"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Limit number of results",
                        "default": 20
                    },
                    "days": {
                        "type": "integer",
                        "description": "Number of days for cleanup operations",
                        "default": 30
                    }
                },
                "required": ["action"]
            }
        )

    async def execute(
        self,
        action: str,
        session_id: Optional[str] = None,
        checkpoint_id: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        output_file: Optional[str] = None,
        limit: int = 20,
        days: int = 30,
        **kwargs
    ) -> ToolResult:
        """Execute session management action."""

        try:
            if action == "list_sessions":
                sessions = await self.session_manager.list_sessions(limit=limit)

                # Format session list
                if not sessions:
                    content = "No sessions found."
                else:
                    lines = ["## Available Sessions", ""]
                    for session in sessions:
                        created = time.strftime(
                            '%Y-%m-%d %H:%M:%S',
                            time.localtime(session['created_at'])
                        )
                        updated = time.strftime(
                            '%Y-%m-%d %H:%M:%S',
                            time.localtime(session['updated_at'])
                        )

                        lines.extend([
                            f"**Session ID:** `{session['id']}`",
                            f"**Created:** {created}",
                            f"**Updated:** {updated}",
                            f"**Messages:** {session['message_count']}",
                            f"**Has Context:** {session['has_context']}",
                        ])

                        if session.get('preview'):
                            lines.append(f"**Preview:** {session['preview']}")

                        lines.append("")

                    content = "\n".join(lines)

                return ToolResult(
                    success=True,
                    content=content,
                    metadata={"sessions_count": len(sessions), "sessions": sessions}
                )

            elif action == "load_session":
                if not session_id:
                    return ToolResult(
                        success=False,
                        content="Session ID required for load operation"
                    )

                session = await self.session_manager.load_session(session_id)
                if not session:
                    return ToolResult(
                        success=False,
                        content=f"Session {session_id} not found"
                    )

                # Format session details
                created = time.strftime(
                    '%Y-%m-%d %H:%M:%S',
                    time.localtime(session.created_at)
                )
                updated = time.strftime(
                    '%Y-%m-%d %H:%M:%S',
                    time.localtime(session.updated_at)
                )

                lines = [
                    f"## Session: {session.id}",
                    f"**Created:** {created}",
                    f"**Updated:** {updated}",
                    f"**Messages:** {len(session.messages)}",
                    ""
                ]

                if session.context:
                    lines.extend([
                        "### Project Context",
                        f"**Root:** {session.context.project_root}",
                        f"**Files:** {len(session.context.files)}",
                        ""
                    ])

                # Show recent messages
                lines.append("### Recent Messages")
                recent_messages = session.messages[-5:] if len(session.messages) > 5 else session.messages

                for i, msg in enumerate(recent_messages):
                    role_icon = "👤" if msg.role == "user" else "🤖"
                    lines.extend([
                        f"**{role_icon} {msg.role.title()}:** {msg.content[:100]}{'...' if len(msg.content) > 100 else ''}",
                        ""
                    ])

                return ToolResult(
                    success=True,
                    content="\n".join(lines),
                    metadata={"session": session.to_dict()}
                )

            elif action == "delete_session":
                if not session_id:
                    return ToolResult(
                        success=False,
                        content="Session ID required for delete operation"
                    )

                success = await self.session_manager.delete_session(session_id)

                if success:
                    return ToolResult(
                        success=True,
                        content=f"Session {session_id} deleted successfully"
                    )
                else:
                    return ToolResult(
                        success=False,
                        content=f"Failed to delete session {session_id}"
                    )

            elif action == "export_session":
                if not session_id or not output_file:
                    return ToolResult(
                        success=False,
                        content="Session ID and output file required for export"
                    )

                session = await self.session_manager.load_session(session_id)
                if not session:
                    return ToolResult(
                        success=False,
                        content=f"Session {session_id} not found"
                    )

                from pathlib import Path
                await export_session_to_markdown(session, Path(output_file))

                return ToolResult(
                    success=True,
                    content=f"Session exported to {output_file}"
                )

            elif action == "create_checkpoint":
                if not session_id:
                    return ToolResult(
                        success=False,
                        content="Session ID required for checkpoint creation"
                    )

                session = await self.session_manager.load_session(session_id)
                if not session:
                    return ToolResult(
                        success=False,
                        content=f"Session {session_id} not found"
                    )

                checkpoint_id = await self.checkpoint_manager.create_checkpoint(
                    session_id=session_id,
                    messages=session.messages,
                    context=session.context,
                    tags=set(tags) if tags else None,
                    description=description
                )

                return ToolResult(
                    success=True,
                    content=f"Checkpoint created with ID: {checkpoint_id}",
                    metadata={"checkpoint_id": checkpoint_id}
                )

            elif action == "list_checkpoints":
                checkpoints = await self.checkpoint_manager.list_checkpoints(
                    session_id=session_id,
                    tags=set(tags) if tags else None,
                    limit=limit
                )

                if not checkpoints:
                    content = "No checkpoints found."
                else:
                    lines = ["## Available Checkpoints", ""]
                    for checkpoint in checkpoints:
                        timestamp = time.strftime(
                            '%Y-%m-%d %H:%M:%S',
                            time.localtime(checkpoint['timestamp'])
                        )

                        lines.extend([
                            f"**Checkpoint ID:** `{checkpoint['id']}`",
                            f"**Session:** `{checkpoint['session_id']}`",
                            f"**Created:** {timestamp}",
                            f"**Messages:** {checkpoint['message_count']}",
                        ])

                        if checkpoint.get('description'):
                            lines.append(f"**Description:** {checkpoint['description']}")

                        if checkpoint.get('tags'):
                            lines.append(f"**Tags:** {', '.join(checkpoint['tags'])}")

                        if checkpoint.get('last_message_preview'):
                            lines.append(f"**Last Message:** {checkpoint['last_message_preview']}")

                        lines.append("")

                    content = "\n".join(lines)

                return ToolResult(
                    success=True,
                    content=content,
                    metadata={"checkpoints_count": len(checkpoints), "checkpoints": checkpoints}
                )

            elif action == "resume_checkpoint":
                if not checkpoint_id:
                    return ToolResult(
                        success=False,
                        content="Checkpoint ID required for resume operation"
                    )

                result = await self.checkpoint_manager.resume_from_checkpoint(
                    checkpoint_id, self.session_manager
                )

                if not result:
                    return ToolResult(
                        success=False,
                        content=f"Failed to resume from checkpoint {checkpoint_id}"
                    )

                new_session, exec_state = result

                return ToolResult(
                    success=True,
                    content=f"Resumed conversation in new session: {new_session.id}",
                    metadata={
                        "new_session_id": new_session.id,
                        "execution_state": exec_state,
                        "original_checkpoint": checkpoint_id
                    }
                )

            elif action == "branch_checkpoint":
                if not checkpoint_id:
                    return ToolResult(
                        success=False,
                        content="Checkpoint ID required for branch operation"
                    )

                # For branching, we'll create an empty branch that can be continued
                branch_session = await self.checkpoint_manager.branch_from_checkpoint(
                    checkpoint_id=checkpoint_id,
                    new_messages=[],  # Empty - will be filled by subsequent conversation
                    session_manager=self.session_manager,
                    branch_description=description
                )

                if not branch_session:
                    return ToolResult(
                        success=False,
                        content=f"Failed to create branch from checkpoint {checkpoint_id}"
                    )

                return ToolResult(
                    success=True,
                    content=f"Created new conversation branch: {branch_session.id}",
                    metadata={
                        "branch_session_id": branch_session.id,
                        "original_checkpoint": checkpoint_id
                    }
                )

            elif action == "delete_checkpoint":
                if not checkpoint_id:
                    return ToolResult(
                        success=False,
                        content="Checkpoint ID required for delete operation"
                    )

                success = await self.checkpoint_manager.delete_checkpoint(checkpoint_id)

                if success:
                    return ToolResult(
                        success=True,
                        content=f"Checkpoint {checkpoint_id} deleted successfully"
                    )
                else:
                    return ToolResult(
                        success=False,
                        content=f"Failed to delete checkpoint {checkpoint_id}"
                    )

            elif action == "cleanup_old":
                sessions_deleted = await self.session_manager.cleanup_old_sessions(days)
                checkpoints_deleted = await self.checkpoint_manager.cleanup_old_checkpoints(days)

                return ToolResult(
                    success=True,
                    content=f"Cleanup completed: {sessions_deleted} sessions and {checkpoints_deleted} checkpoints deleted",
                    metadata={
                        "sessions_deleted": sessions_deleted,
                        "checkpoints_deleted": checkpoints_deleted,
                        "days": days
                    }
                )

            else:
                return ToolResult(
                    success=False,
                    content=f"Unknown action: {action}"
                )

        except Exception as e:
            return ToolResult(
                success=False,
                content=f"Session management error: {str(e)}",
                metadata={"error": str(e), "action": action}
            )
