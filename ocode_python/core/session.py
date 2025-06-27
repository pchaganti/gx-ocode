"""
Session management for OCode conversations.
"""

import json
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from .api_client import Message
from .context_manager import ProjectContext


@dataclass
class Session:
    """Represents a conversation session."""

    id: str
    created_at: float
    updated_at: float
    messages: List[Message]
    context: Optional[ProjectContext] = None
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary for serialization.

        Handles custom serialization for Path objects in the context.

        Returns:
            Dictionary representation suitable for JSON serialization.
        """
        result = {
            "id": self.id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "messages": [asdict(msg) for msg in self.messages],
            "context": None,
            "metadata": self.metadata,
        }

        # Custom serialization for context to handle Path objects
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
    def from_dict(cls, data: Dict[str, Any]) -> "Session":
        """Create session from dictionary.

        Reconstructs a Session object from its serialized form,
        including proper Path object reconstruction in the context.

        Args:
            data: Dictionary containing session data.

        Returns:
            Reconstructed Session object.
        """
        messages = [Message(**msg) for msg in data.get("messages", [])]
        context = None
        if data.get("context"):
            # Reconstruct ProjectContext
            context_data = data["context"]
            from .context_manager import FileInfo

            # Reconstruct file_info
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
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            messages=messages,
            context=context,
            metadata=data.get("metadata", {}),
        )


class SessionManager:
    """
    Manages OCode conversation sessions.

    Provides session persistence, loading, and management capabilities.
    """

    def __init__(self, sessions_dir: Optional[Path] = None):
        """
        Initialize session manager.

        Args:
            sessions_dir: Directory to store session files
        """
        if sessions_dir:
            self.sessions_dir = sessions_dir
        else:
            # Default to .ocode/sessions in current directory or home
            if (Path.cwd() / ".ocode").exists():
                self.sessions_dir = Path.cwd() / ".ocode" / "sessions"
            else:
                self.sessions_dir = Path.home() / ".ocode" / "sessions"

        self.sessions_dir.mkdir(parents=True, exist_ok=True)

        # Session cache
        self._session_cache: Dict[str, Session] = {}

    def _get_session_file(self, session_id: str) -> Path:
        """Get the file path for a session.

        Args:
            session_id: The session identifier.

        Returns:
            Path to the session JSON file.
        """
        return self.sessions_dir / f"{session_id}.json"

    async def create_session(
        self,
        messages: Optional[List[Message]] = None,
        context: Optional[ProjectContext] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Session:
        """
        Create a new session.

        Args:
            messages: Initial messages
            context: Project context
            metadata: Additional metadata

        Returns:
            New session instance
        """
        session_id = str(uuid.uuid4())
        current_time = time.time()

        session = Session(
            id=session_id,
            created_at=current_time,
            updated_at=current_time,
            messages=messages or [],
            context=context,
            metadata=metadata or {},
        )

        # Cache the session
        self._session_cache[session_id] = session

        return session

    async def save_session(
        self,
        messages: List[Message],
        context: Optional[ProjectContext] = None,
        session_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Save a session to persistent storage.

        Args:
            messages: Conversation messages
            context: Project context
            session_id: Existing session ID (creates new if None)
            metadata: Additional metadata

        Returns:
            Session ID
        """
        if session_id and session_id in self._session_cache:
            # Update existing session
            session = self._session_cache[session_id]
            session.messages = messages
            session.context = context
            session.updated_at = time.time()
            if metadata:
                if session.metadata is None:
                    session.metadata = {}
                session.metadata.update(metadata)
        else:
            # Create new session
            session = await self.create_session(messages, context, metadata)
            session_id = session.id

        # Save to file
        session_file = self._get_session_file(session_id)
        try:
            with open(session_file, "w", encoding="utf-8") as f:
                json.dump(session.to_dict(), f, indent=2, default=str)
        except Exception as e:
            raise RuntimeError(f"Failed to save session: {str(e)}")

        return session_id

    async def load_session(self, session_id: str) -> Optional[Session]:
        """
        Load a session from storage.

        Args:
            session_id: Session ID to load

        Returns:
            Session instance or None if not found
        """
        # Check cache first
        if session_id in self._session_cache:
            return self._session_cache[session_id]

        # Load from file
        session_file = self._get_session_file(session_id)
        if not session_file.exists():
            return None

        try:
            with open(session_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            session = Session.from_dict(data)
            self._session_cache[session_id] = session
            return session

        except Exception as e:
            print(f"Failed to load session {session_id}: {str(e)}")
            return None

    async def list_sessions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        List available sessions.

        Args:
            limit: Maximum number of sessions to return

        Returns:
            List of session summaries
        """
        sessions = []

        # Get all session files
        session_files = list(self.sessions_dir.glob("*.json"))
        session_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

        for session_file in session_files[:limit]:
            try:
                with open(session_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Create summary
                summary = {
                    "id": data["id"],
                    "created_at": data["created_at"],
                    "updated_at": data["updated_at"],
                    "message_count": len(data.get("messages", [])),
                    "has_context": bool(data.get("context")),
                    "metadata": data.get("metadata", {}),
                }

                # Add first user message as preview
                messages = data.get("messages", [])
                for msg in messages:
                    if msg.get("role") == "user":
                        content = msg.get("content", "")
                        summary["preview"] = (
                            content[:100] + "..." if len(content) > 100 else content
                        )
                        break

                sessions.append(summary)

            except Exception:
                # Skip corrupted session files
                continue  # nosec B112

        return sessions

    async def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.

        Args:
            session_id: Session ID to delete

        Returns:
            True if deleted successfully
        """
        try:
            # Remove from cache
            if session_id in self._session_cache:
                del self._session_cache[session_id]

            # Remove file
            session_file = self._get_session_file(session_id)
            if session_file.exists():
                session_file.unlink()

            return True

        except Exception:
            return False

    async def cleanup_old_sessions(self, days: int = 30) -> int:
        """
        Clean up sessions older than specified days.

        Args:
            days: Number of days to keep sessions

        Returns:
            Number of sessions deleted
        """
        cutoff_time = time.time() - (days * 24 * 60 * 60)
        deleted_count = 0

        for session_file in self.sessions_dir.glob("*.json"):
            try:
                # Check file modification time
                if session_file.stat().st_mtime < cutoff_time:
                    session_file.unlink()
                    deleted_count += 1

                    # Remove from cache if present
                    session_id = session_file.stem
                    if session_id in self._session_cache:
                        del self._session_cache[session_id]

            except Exception:
                continue  # nosec B112

        return deleted_count

    def get_last_session_id(self) -> Optional[str]:
        """Get the ID of the most recently updated session.

        Scans session files to find the one with the most recent
        modification time.

        Returns:
            Session ID string, or None if no sessions exist.
        """
        latest_file = None
        latest_time = 0.0

        for session_file in self.sessions_dir.glob("*.json"):
            try:
                mtime = session_file.stat().st_mtime
                if mtime > latest_time:
                    latest_time = mtime
                    latest_file = session_file
            except Exception:
                continue  # nosec B112

        return latest_file.stem if latest_file else None


# Session utilities
async def export_session_to_markdown(session: Session, output_file: Path) -> None:
    """Export session to markdown format.

    Creates a formatted markdown file with session metadata,
    project context, and the full conversation history.

    Args:
        session: Session object to export.
        output_file: Path where the markdown file will be written.
    """
    lines = [
        f"# OCode Session: {session.id}",
        f"Created: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(session.created_at))}",  # noqa: E501
        f"Updated: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(session.updated_at))}",  # noqa: E501
        "",
    ]

    # Add context information
    if session.context:
        lines.extend(
            [
                "## Project Context",
                f"Root: {session.context.project_root}",
                f"Files: {len(session.context.files)}",
                "",
            ]
        )

        if session.context.git_info:
            lines.extend(
                [
                    "### Git Information",
                    f"Branch: {session.context.git_info.get('branch', 'unknown')}",
                    f"Commit: {session.context.git_info.get('commit', 'unknown')}",
                    "",
                ]
            )

    # Add conversation
    lines.append("## Conversation")
    lines.append("")

    for i, message in enumerate(session.messages):
        role_icon = "👤" if message.role == "user" else "🤖"
        lines.extend(
            [f"### {role_icon} {message.role.title()} {i + 1}", "", message.content, ""]
        )

    # Write to file
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


async def main() -> None:
    """Example usage of SessionManager."""
    manager = SessionManager()

    # Create a test session
    messages = [
        Message("user", "Hello, can you help me with my Python project?"),
        Message(
            "assistant", "Of course! I'd be happy to help you with your Python project."
        ),
    ]

    session_id = await manager.save_session(messages)
    print(f"Created session: {session_id}")

    # Load the session
    loaded_session = await manager.load_session(session_id)
    if loaded_session:
        print(f"Loaded session with {len(loaded_session.messages)} messages")

    # List sessions
    sessions = await manager.list_sessions()
    print(f"Found {len(sessions)} sessions")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
