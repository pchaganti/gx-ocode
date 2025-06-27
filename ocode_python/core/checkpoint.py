"""
Advanced checkpointing and resume functionality for OCode sessions.
"""

import asyncio
import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from .api_client import Message
from .context_manager import ProjectContext
from .session import Session, SessionManager


@dataclass
class Checkpoint:
    """Represents a conversation checkpoint with execution state."""

    id: str
    session_id: str
    timestamp: float
    messages: List[Message]
    context: Optional[ProjectContext] = None
    execution_state: Optional[Dict[str, Any]] = None
    tags: Optional[Set[str]] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert checkpoint to dictionary for serialization."""
        result = {
            "id": self.id,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "messages": [asdict(msg) for msg in self.messages],
            "context": None,
            "execution_state": self.execution_state,
            "tags": list(self.tags) if self.tags else [],
            "description": self.description,
            "metadata": self.metadata or {},
        }

        # Custom serialization for context
        if self.context:
            context_dict = {
                "files": {str(k): v for k, v in self.context.files.items()},
                "file_info": {
                    str(k): asdict(v) for k, v in self.context.file_info.items()
                },
                "dependencies": {
                    str(k): [str(p) for p in v]
                    for k, v in self.context.dependencies.items()
                },
                "symbols": {
                    k: [str(p) for p in v] for k, v in self.context.symbols.items()
                },
                "project_root": str(self.context.project_root),
                "git_info": self.context.git_info,
            }
            result["context"] = context_dict

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Checkpoint":
        """Create checkpoint from dictionary."""
        messages = [Message(**msg) for msg in data.get("messages", [])]
        context = None

        if data.get("context"):
            context_data = data["context"]
            from .context_manager import FileInfo

            file_info = {}
            for path_str, info_dict in context_data.get("file_info", {}).items():
                file_info[Path(path_str)] = FileInfo(**info_dict)

            context = ProjectContext(
                files={Path(k): v for k, v in context_data.get("files", {}).items()},
                file_info=file_info,
                dependencies={
                    Path(k): {Path(p) for p in v}
                    for k, v in context_data.get("dependencies", {}).items()
                },
                symbols={
                    k: [Path(p) for p in v]
                    for k, v in context_data.get("symbols", {}).items()
                },
                project_root=Path(context_data.get("project_root", ".")),
                git_info=context_data.get("git_info"),
            )

        return cls(
            id=data["id"],
            session_id=data["session_id"],
            timestamp=data["timestamp"],
            messages=messages,
            context=context,
            execution_state=data.get("execution_state"),
            tags=set(data.get("tags", [])),
            description=data.get("description"),
            metadata=data.get("metadata", {}),
        )


class CheckpointManager:
    """Advanced checkpoint management with branching and resumption capabilities."""

    def __init__(self, checkpoints_dir: Optional[Path] = None):
        """Initialize checkpoint manager.

        Args:
            checkpoints_dir: Directory to store checkpoint files
        """
        if checkpoints_dir:
            self.checkpoints_dir = checkpoints_dir
        else:
            # Default to .ocode/checkpoints
            if (Path.cwd() / ".ocode").exists():
                self.checkpoints_dir = Path.cwd() / ".ocode" / "checkpoints"
            else:
                self.checkpoints_dir = Path.home() / ".ocode" / "checkpoints"

        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)
        self._checkpoint_cache: Dict[str, Checkpoint] = {}

    def _get_checkpoint_file(self, checkpoint_id: str) -> Path:
        """Get checkpoint file path."""
        return self.checkpoints_dir / f"{checkpoint_id}.json"

    async def create_checkpoint(
        self,
        session_id: str,
        messages: List[Message],
        context: Optional[ProjectContext] = None,
        execution_state: Optional[Dict[str, Any]] = None,
        tags: Optional[Set[str]] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create a new checkpoint.

        Args:
            session_id: Associated session ID
            messages: Current conversation messages
            context: Project context at checkpoint time
            execution_state: Current execution state
            tags: Descriptive tags for the checkpoint
            description: Human-readable description
            metadata: Additional metadata

        Returns:
            Checkpoint ID
        """
        import uuid

        checkpoint_id = str(uuid.uuid4())

        checkpoint = Checkpoint(
            id=checkpoint_id,
            session_id=session_id,
            timestamp=time.time(),
            messages=messages.copy(),
            context=context,
            execution_state=execution_state,
            tags=tags or set(),
            description=description,
            metadata=metadata or {},
        )

        # Save checkpoint
        await self.save_checkpoint(checkpoint)

        return checkpoint_id

    async def save_checkpoint(self, checkpoint: Checkpoint) -> None:
        """Save checkpoint to storage."""
        checkpoint_file = self._get_checkpoint_file(checkpoint.id)

        try:
            with open(checkpoint_file, "w", encoding="utf-8") as f:
                json.dump(checkpoint.to_dict(), f, indent=2, default=str)

            # Cache the checkpoint
            self._checkpoint_cache[checkpoint.id] = checkpoint

        except Exception as e:
            raise RuntimeError(f"Failed to save checkpoint: {str(e)}")

    async def load_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """Load checkpoint from storage.

        Args:
            checkpoint_id: Checkpoint ID to load

        Returns:
            Checkpoint instance or None if not found
        """
        # Check cache first
        if checkpoint_id in self._checkpoint_cache:
            return self._checkpoint_cache[checkpoint_id]

        checkpoint_file = self._get_checkpoint_file(checkpoint_id)
        if not checkpoint_file.exists():
            return None

        try:
            with open(checkpoint_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            checkpoint = Checkpoint.from_dict(data)
            self._checkpoint_cache[checkpoint_id] = checkpoint
            return checkpoint

        except Exception as e:
            print(f"Failed to load checkpoint {checkpoint_id}: {str(e)}")
            return None

    async def list_checkpoints(
        self,
        session_id: Optional[str] = None,
        tags: Optional[Set[str]] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """List checkpoints with optional filtering.

        Args:
            session_id: Filter by session ID
            tags: Filter by tags (any matching tag)
            limit: Maximum number of results

        Returns:
            List of checkpoint summaries
        """
        checkpoints = []

        # Get all checkpoint files
        checkpoint_files = list(self.checkpoints_dir.glob("*.json"))
        checkpoint_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

        for checkpoint_file in checkpoint_files:
            try:
                with open(checkpoint_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Apply filters
                if session_id and data.get("session_id") != session_id:
                    continue

                if tags:
                    checkpoint_tags = set(data.get("tags", []))
                    if not tags.intersection(checkpoint_tags):
                        continue

                # Create summary
                summary = {
                    "id": data["id"],
                    "session_id": data["session_id"],
                    "timestamp": data["timestamp"],
                    "message_count": len(data.get("messages", [])),
                    "has_context": bool(data.get("context")),
                    "has_execution_state": bool(data.get("execution_state")),
                    "tags": data.get("tags", []),
                    "description": data.get("description"),
                    "metadata": data.get("metadata", {}),
                }

                # Add message preview
                messages = data.get("messages", [])
                if messages:
                    last_msg = messages[-1]
                    content = last_msg.get("content", "")
                    summary["last_message_preview"] = (
                        content[:100] + "..." if len(content) > 100 else content
                    )
                    summary["last_message_role"] = last_msg.get("role")

                checkpoints.append(summary)

                if len(checkpoints) >= limit:
                    break

            except Exception:  # nosec B112
                # Skip corrupted checkpoint files
                continue

        return checkpoints

    async def resume_from_checkpoint(
        self, checkpoint_id: str, session_manager: SessionManager
    ) -> Optional[Tuple[Session, Dict[str, Any]]]:
        """Resume conversation from a checkpoint.

        Args:
            checkpoint_id: Checkpoint to resume from
            session_manager: Session manager for creating new session

        Returns:
            Tuple of (new_session, execution_state) or None if failed
        """
        checkpoint = await self.load_checkpoint(checkpoint_id)
        if not checkpoint:
            return None

        # Create new session from checkpoint
        new_session = await session_manager.create_session(
            messages=checkpoint.messages.copy(),
            context=checkpoint.context,
            metadata={
                "resumed_from_checkpoint": checkpoint_id,
                "original_session": checkpoint.session_id,
                "checkpoint_timestamp": checkpoint.timestamp,
                **(checkpoint.metadata or {}),
            },
        )

        # Return session and execution state for restoration
        return new_session, checkpoint.execution_state or {}

    async def branch_from_checkpoint(
        self,
        checkpoint_id: str,
        new_messages: List[Message],
        session_manager: SessionManager,
        branch_description: Optional[str] = None,
    ) -> Optional[Session]:
        """Create a new conversation branch from a checkpoint.

        Args:
            checkpoint_id: Checkpoint to branch from
            new_messages: New messages to start the branch
            session_manager: Session manager for creating new session
            branch_description: Description of the branch

        Returns:
            New session for the branch or None if failed
        """
        checkpoint = await self.load_checkpoint(checkpoint_id)
        if not checkpoint:
            return None

        # Combine checkpoint messages with new messages
        branch_messages = checkpoint.messages.copy() + new_messages

        # Create new session for branch
        branch_session = await session_manager.create_session(
            messages=branch_messages,
            context=checkpoint.context,
            metadata={
                "branched_from_checkpoint": checkpoint_id,
                "original_session": checkpoint.session_id,
                "branch_description": branch_description,
                "branch_timestamp": time.time(),
                **(checkpoint.metadata or {}),
            },
        )

        return branch_session

    async def auto_checkpoint(
        self,
        session_id: str,
        messages: List[Message],
        context: Optional[ProjectContext] = None,
        execution_state: Optional[Dict[str, Any]] = None,
        interval_messages: int = 10,
    ) -> Optional[str]:
        """Automatically create checkpoints based on message intervals.

        Args:
            session_id: Current session ID
            messages: Current messages
            context: Current context
            execution_state: Current execution state
            interval_messages: Create checkpoint every N messages

        Returns:
            Checkpoint ID if created, None otherwise
        """
        if len(messages) % interval_messages == 0 and len(messages) > 0:
            return await self.create_checkpoint(
                session_id=session_id,
                messages=messages,
                context=context,
                execution_state=execution_state,
                tags={"auto"},
                description=f"Auto-checkpoint at {len(messages)} messages",
            )
        return None

    async def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """Delete a checkpoint.

        Args:
            checkpoint_id: Checkpoint ID to delete

        Returns:
            True if deleted successfully
        """
        try:
            # Remove from cache
            if checkpoint_id in self._checkpoint_cache:
                del self._checkpoint_cache[checkpoint_id]

            # Remove file
            checkpoint_file = self._get_checkpoint_file(checkpoint_id)
            if checkpoint_file.exists():
                checkpoint_file.unlink()

            return True

        except Exception:
            return False

    async def cleanup_old_checkpoints(self, days: int = 30) -> int:
        """Clean up checkpoints older than specified days.

        Args:
            days: Number of days to keep checkpoints

        Returns:
            Number of checkpoints deleted
        """
        cutoff_time = time.time() - (days * 24 * 60 * 60)
        deleted_count = 0

        for checkpoint_file in self.checkpoints_dir.glob("*.json"):
            try:
                if checkpoint_file.stat().st_mtime < cutoff_time:
                    checkpoint_file.unlink()
                    deleted_count += 1

                    # Remove from cache if present
                    checkpoint_id = checkpoint_file.stem
                    if checkpoint_id in self._checkpoint_cache:
                        del self._checkpoint_cache[checkpoint_id]

            except Exception:  # nosec B112
                # Skip unreadable checkpoint files during cleanup
                continue

        return deleted_count


# Utility functions
async def export_checkpoint_to_markdown(
    checkpoint: Checkpoint, output_file: Path
) -> None:
    """Export checkpoint to markdown format.

    Args:
        checkpoint: Checkpoint to export
        output_file: Path for output file
    """
    lines = [
        f"# OCode Checkpoint: {checkpoint.id}",
        f"Session: {checkpoint.session_id}",
        f"Created: "
        f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(checkpoint.timestamp))}",
        "",
    ]

    if checkpoint.description:
        lines.extend(["## Description", checkpoint.description, ""])

    if checkpoint.tags:
        lines.extend(["## Tags", ", ".join(sorted(checkpoint.tags)), ""])

    # Add context information
    if checkpoint.context:
        lines.extend(
            [
                "## Project Context",
                f"Root: {checkpoint.context.project_root}",
                f"Files: {len(checkpoint.context.files)}",
                "",
            ]
        )

    # Add execution state
    if checkpoint.execution_state:
        lines.extend(
            [
                "## Execution State",
                "```json",
                json.dumps(checkpoint.execution_state, indent=2),
                "```",
                "",
            ]
        )

    # Add conversation
    lines.extend(["## Conversation", ""])

    for i, message in enumerate(checkpoint.messages):
        role_icon = "👤" if message.role == "user" else "🤖"
        lines.extend(
            [f"### {role_icon} {message.role.title()} {i + 1}", "", message.content, ""]
        )

    # Write to file
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


async def main() -> None:
    """Example usage of CheckpointManager."""
    checkpoint_manager = CheckpointManager()
    session_manager = SessionManager()

    # Create test session
    messages = [
        Message("user", "Hello, can you help me refactor this function?"),
        Message(
            "assistant", "Of course! Please share the function you'd like to refactor."
        ),
        Message("user", "Here's the function: def complex_function()..."),
    ]

    session_id = await session_manager.save_session(messages)
    print(f"Created session: {session_id}")

    # Create checkpoint
    checkpoint_id = await checkpoint_manager.create_checkpoint(
        session_id=session_id,
        messages=messages,
        tags={"refactoring", "function"},
        description="Before starting function refactoring",
    )
    print(f"Created checkpoint: {checkpoint_id}")

    # Continue conversation
    messages.append(Message("assistant", "I'll help you refactor this function..."))
    messages.append(Message("user", "Actually, let me try a different approach"))

    # Resume from checkpoint to try different approach
    result = await checkpoint_manager.resume_from_checkpoint(
        checkpoint_id, session_manager
    )
    if result:
        resumed_session, exec_state = result
        print(f"Resumed conversation in new session: {resumed_session.id}")

    # List checkpoints
    checkpoints = await checkpoint_manager.list_checkpoints()
    print(f"Found {len(checkpoints)} checkpoints")


if __name__ == "__main__":
    asyncio.run(main())
