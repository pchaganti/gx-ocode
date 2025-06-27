"""
Session and checkpoint management tool for interactive conversation control.
"""

import time

from ..core.checkpoint import CheckpointManager
from ..core.session import SessionManager, export_session_to_markdown
from .base import Tool, ToolDefinition, ToolParameter, ToolResult


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
            description=(
                "Manage conversation sessions and checkpoints - save, load, "
                "resume, and branch conversations"
            ),
            category="Session Management",
            parameters=[
                ToolParameter(
                    name="action",
                    type="string",
                    description="The session management action to perform",
                    required=True,
                ),
                ToolParameter(
                    name="session_id",
                    type="string",
                    description="Session ID for load/delete/export operations",
                    required=False,
                ),
                ToolParameter(
                    name="checkpoint_id",
                    type="string",
                    description="Checkpoint ID for checkpoint operations",
                    required=False,
                ),
                ToolParameter(
                    name="description",
                    type="string",
                    description="Description for checkpoints or sessions",
                    required=False,
                ),
                ToolParameter(
                    name="tags",
                    type="array",
                    description="Tags for categorizing checkpoints",
                    required=False,
                ),
                ToolParameter(
                    name="output_file",
                    type="string",
                    description="Output file path for exports",
                    required=False,
                ),
                ToolParameter(
                    name="limit",
                    type="number",
                    description="Limit number of results",
                    required=False,
                    default=20,
                ),
                ToolParameter(
                    name="days",
                    type="number",
                    description="Number of days for cleanup operations",
                    required=False,
                    default=30,
                ),
            ],
        )

    async def execute(self, **kwargs) -> ToolResult:
        """Execute session management action."""
        action = kwargs.get("action", "")
        session_id = kwargs.get("session_id")
        checkpoint_id = kwargs.get("checkpoint_id")
        description = kwargs.get("description")
        tags = kwargs.get("tags")
        output_file = kwargs.get("output_file")
        limit = kwargs.get("limit", 20)
        days = kwargs.get("days", 30)

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
                            "%Y-%m-%d %H:%M:%S", time.localtime(session["created_at"])
                        )
                        updated = time.strftime(
                            "%Y-%m-%d %H:%M:%S", time.localtime(session["updated_at"])
                        )

                        lines.extend(
                            [
                                f"**Session ID:** `{session['id']}`",
                                f"**Created:** {created}",
                                f"**Updated:** {updated}",
                                f"**Messages:** {session['message_count']}",
                                f"**Has Context:** {session['has_context']}",
                            ]
                        )

                        if session.get("preview"):
                            lines.append(f"**Preview:** {session['preview']}")

                        lines.append("")

                    content = "\n".join(lines)

                return ToolResult(
                    success=True,
                    output=content,
                    metadata={"sessions_count": len(sessions), "sessions": sessions},
                )

            elif action == "load_session":
                if not session_id:
                    return ToolResult(
                        success=False,
                        output="",
                        error="Session ID required for load operation",
                    )

                session_obj = await self.session_manager.load_session(session_id)
                if not session_obj:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Session {session_id} not found",
                    )

                # Format session details
                created = time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime(session_obj.created_at)
                )
                updated = time.strftime(
                    "%Y-%m-%d %H:%M:%S", time.localtime(session_obj.updated_at)
                )

                lines = [
                    f"## Session: {session_obj.id}",
                    f"**Created:** {created}",
                    f"**Updated:** {updated}",
                    f"**Messages:** {len(session_obj.messages)}",
                    "",
                ]

                if session_obj.context:
                    lines.extend(
                        [
                            "### Project Context",
                            f"**Root:** {session_obj.context.project_root}",
                            f"**Files:** {len(session_obj.context.files)}",
                            "",
                        ]
                    )

                # Show recent messages
                lines.append("### Recent Messages")
                recent_messages = (
                    session_obj.messages[-5:]
                    if len(session_obj.messages) > 5
                    else session_obj.messages
                )

                for i, msg in enumerate(recent_messages):
                    role_icon = "👤" if msg.role == "user" else "🤖"
                    lines.extend(
                        [
                            f"**{role_icon} {msg.role.title()}:** "
                            f"{msg.content[:100]}"
                            f"{'...' if len(msg.content) > 100 else ''}",
                            "",
                        ]
                    )

                return ToolResult(
                    success=True,
                    output="\n".join(lines),
                    metadata={"session": session_obj.to_dict()},
                )

            elif action == "delete_session":
                if not session_id:
                    return ToolResult(
                        success=False,
                        output="",
                        error="Session ID required for delete operation",
                    )

                success = await self.session_manager.delete_session(session_id)

                if success:
                    return ToolResult(
                        success=True,
                        output=f"Session {session_id} deleted successfully",
                    )
                else:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Failed to delete session {session_id}",
                    )

            elif action == "export_session":
                if not session_id or not output_file:
                    return ToolResult(
                        success=False,
                        output="",
                        error="Session ID and output file required for export",
                    )

                session_obj = await self.session_manager.load_session(session_id)
                if not session_obj:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Session {session_id} not found",
                    )

                from pathlib import Path

                await export_session_to_markdown(session_obj, Path(output_file))

                return ToolResult(
                    success=True, output=f"Session exported to {output_file}"
                )

            elif action == "create_checkpoint":
                if not session_id:
                    return ToolResult(
                        success=False,
                        output="",
                        error="Session ID required for checkpoint creation",
                    )

                session_obj = await self.session_manager.load_session(session_id)
                if not session_obj:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Session {session_id} not found",
                    )

                checkpoint_id = await self.checkpoint_manager.create_checkpoint(
                    session_id=session_id,
                    messages=session_obj.messages,
                    context=session_obj.context,
                    tags=set(tags) if tags else None,
                    description=description,
                )

                return ToolResult(
                    success=True,
                    output=f"Checkpoint created with ID: {checkpoint_id}",
                    metadata={"checkpoint_id": checkpoint_id},
                )

            elif action == "list_checkpoints":
                checkpoints = await self.checkpoint_manager.list_checkpoints(
                    session_id=session_id, tags=set(tags) if tags else None, limit=limit
                )

                if not checkpoints:
                    content = "No checkpoints found."
                else:
                    lines = ["## Available Checkpoints", ""]
                    for checkpoint in checkpoints:
                        timestamp = time.strftime(
                            "%Y-%m-%d %H:%M:%S", time.localtime(checkpoint["timestamp"])
                        )

                        lines.extend(
                            [
                                f"**Checkpoint ID:** `{checkpoint['id']}`",
                                f"**Session:** `{checkpoint['session_id']}`",
                                f"**Created:** {timestamp}",
                                f"**Messages:** {checkpoint['message_count']}",
                            ]
                        )

                        if checkpoint.get("description"):
                            lines.append(
                                f"**Description:** {checkpoint['description']}"
                            )

                        if checkpoint.get("tags"):
                            lines.append(f"**Tags:** {', '.join(checkpoint['tags'])}")

                        if checkpoint.get("last_message_preview"):
                            lines.append(
                                f"**Last Message:** "
                                f"{checkpoint['last_message_preview']}"
                            )

                        lines.append("")

                    content = "\n".join(lines)

                return ToolResult(
                    success=True,
                    output=content,
                    metadata={
                        "checkpoints_count": len(checkpoints),
                        "checkpoints": checkpoints,
                    },
                )

            elif action == "resume_checkpoint":
                if not checkpoint_id:
                    return ToolResult(
                        success=False,
                        output="",
                        error="Checkpoint ID required for resume operation",
                    )

                result = await self.checkpoint_manager.resume_from_checkpoint(
                    checkpoint_id, self.session_manager
                )

                if not result:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Failed to resume from checkpoint {checkpoint_id}",
                    )

                new_session, exec_state = result

                return ToolResult(
                    success=True,
                    output=f"Resumed conversation in new session: {new_session.id}",
                    metadata={
                        "new_session_id": new_session.id,
                        "execution_state": exec_state,
                        "original_checkpoint": checkpoint_id,
                    },
                )

            elif action == "branch_checkpoint":
                if not checkpoint_id:
                    return ToolResult(
                        success=False,
                        output="",
                        error="Checkpoint ID required for branch operation",
                    )

                # For branching, we'll create an empty branch that can be continued
                branch_session = await self.checkpoint_manager.branch_from_checkpoint(
                    checkpoint_id=checkpoint_id,
                    # Empty - will be filled by subsequent conversation
                    new_messages=[],
                    session_manager=self.session_manager,
                    branch_description=description,
                )

                if not branch_session:
                    return ToolResult(
                        success=False,
                        output="",
                        error=(
                            f"Failed to create branch from checkpoint "
                            f"{checkpoint_id}"
                        ),
                    )

                return ToolResult(
                    success=True,
                    output=f"Created new conversation branch: {branch_session.id}",
                    metadata={
                        "branch_session_id": branch_session.id,
                        "original_checkpoint": checkpoint_id,
                    },
                )

            elif action == "delete_checkpoint":
                if not checkpoint_id:
                    return ToolResult(
                        success=False,
                        output="",
                        error="Checkpoint ID required for delete operation",
                    )

                success = await self.checkpoint_manager.delete_checkpoint(checkpoint_id)

                if success:
                    return ToolResult(
                        success=True,
                        output=f"Checkpoint {checkpoint_id} deleted successfully",
                    )
                else:
                    return ToolResult(
                        success=False,
                        output="",
                        error=f"Failed to delete checkpoint {checkpoint_id}",
                    )

            elif action == "cleanup_old":
                sessions_deleted = await self.session_manager.cleanup_old_sessions(days)
                checkpoints_deleted = (
                    await self.checkpoint_manager.cleanup_old_checkpoints(days)
                )

                return ToolResult(
                    success=True,
                    output=(
                        f"Cleanup completed: {sessions_deleted} sessions and "
                        f"{checkpoints_deleted} checkpoints deleted"
                    ),
                    metadata={
                        "sessions_deleted": sessions_deleted,
                        "checkpoints_deleted": checkpoints_deleted,
                        "days": days,
                    },
                )

            else:
                return ToolResult(
                    success=False, output="", error=f"Unknown action: {action}"
                )

        except Exception as e:
            return ToolResult(
                success=False,
                output="",
                error=f"Session management error: {str(e)}",
                metadata={"error": str(e), "action": action},
            )
