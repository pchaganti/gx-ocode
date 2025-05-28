"""
Unit tests for session management.
"""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch
from datetime import datetime

from ocode_python.core.session import (
    SessionManager, Session, SessionMetadata, ConversationHistory
)


@pytest.mark.unit
class TestSession:
    """Test Session data class."""
    
    def test_session_creation(self):
        """Test session creation."""
        session = Session(
            id="test-session-123",
            title="Test Session",
            model="test-model",
            created_at=datetime.now(),
            last_accessed=datetime.now(),
            conversation=[
                {"role": "user", "content": "Hello"},
                {"role": "assistant", "content": "Hi there!"}
            ]
        )
        
        assert session.id == "test-session-123"
        assert session.title == "Test Session"
        assert session.model == "test-model"
        assert len(session.conversation) == 2
    
    def test_session_to_dict(self):
        """Test session serialization."""
        now = datetime.now()
        session = Session(
            id="test-123",
            title="Test",
            model="test-model",
            created_at=now,
            last_accessed=now,
            conversation=[{"role": "user", "content": "test"}]
        )
        
        data = session.to_dict()
        
        assert data["id"] == "test-123"
        assert data["title"] == "Test"
        assert data["model"] == "test-model"
        assert len(data["conversation"]) == 1
        assert "created_at" in data
        assert "last_accessed" in data
    
    def test_session_from_dict(self):
        """Test session deserialization."""
        data = {
            "id": "test-123",
            "title": "Test",
            "model": "test-model",
            "created_at": "2023-01-01T12:00:00",
            "last_accessed": "2023-01-01T12:00:00",
            "conversation": [{"role": "user", "content": "test"}],
            "metadata": {}
        }
        
        session = Session.from_dict(data)
        
        assert session.id == "test-123"
        assert session.title == "Test"
        assert session.model == "test-model"
        assert len(session.conversation) == 1
    
    def test_session_add_message(self):
        """Test adding messages to session."""
        session = Session(
            id="test-123",
            title="Test",
            model="test-model",
            conversation=[]
        )
        
        session.add_message("user", "Hello")
        session.add_message("assistant", "Hi there!")
        
        assert len(session.conversation) == 2
        assert session.conversation[0]["role"] == "user"
        assert session.conversation[1]["role"] == "assistant"
    
    def test_session_get_last_messages(self):
        """Test getting last N messages."""
        session = Session(
            id="test-123",
            title="Test",
            model="test-model",
            conversation=[
                {"role": "user", "content": "Message 1"},
                {"role": "assistant", "content": "Response 1"},
                {"role": "user", "content": "Message 2"},
                {"role": "assistant", "content": "Response 2"},
                {"role": "user", "content": "Message 3"},
            ]
        )
        
        last_3 = session.get_last_messages(3)
        assert len(last_3) == 3
        assert last_3[-1]["content"] == "Message 3"
        
        last_10 = session.get_last_messages(10)
        assert len(last_10) == 5  # All messages


@pytest.mark.unit
class TestSessionManager:
    """Test SessionManager functionality."""
    
    def test_manager_initialization(self, temp_dir: Path):
        """Test session manager initialization."""
        manager = SessionManager(temp_dir)
        
        assert manager.sessions_dir == temp_dir / "sessions"
        assert manager.sessions_dir.exists()
    
    def test_generate_session_id(self, temp_dir: Path):
        """Test session ID generation."""
        manager = SessionManager(temp_dir)
        
        id1 = manager._generate_session_id()
        id2 = manager._generate_session_id()
        
        assert id1 != id2
        assert len(id1) > 10  # Should be reasonably long
        assert id1.replace("-", "").isalnum()  # Should be alphanumeric with dashes
    
    def test_create_session(self, temp_dir: Path):
        """Test session creation."""
        manager = SessionManager(temp_dir)
        
        session = manager.create_session(
            title="Test Session",
            model="test-model"
        )
        
        assert session.title == "Test Session"
        assert session.model == "test-model"
        assert len(session.conversation) == 0
        assert session.id is not None
    
    def test_save_session(self, temp_dir: Path):
        """Test session saving."""
        manager = SessionManager(temp_dir)
        
        session = manager.create_session("Test", "test-model")
        session.add_message("user", "Hello")
        
        success = manager.save_session(session)
        assert success
        
        # Check if file was created
        session_file = manager.sessions_dir / f"{session.id}.json"
        assert session_file.exists()
        
        # Verify content
        with open(session_file) as f:
            data = json.load(f)
            assert data["id"] == session.id
            assert len(data["conversation"]) == 1
    
    def test_load_session(self, temp_dir: Path):
        """Test session loading."""
        manager = SessionManager(temp_dir)
        
        # Create and save session
        original_session = manager.create_session("Test", "test-model")
        original_session.add_message("user", "Hello")
        manager.save_session(original_session)
        
        # Load session
        loaded_session = manager.load_session(original_session.id)
        
        assert loaded_session is not None
        assert loaded_session.id == original_session.id
        assert loaded_session.title == original_session.title
        assert len(loaded_session.conversation) == 1
    
    def test_load_nonexistent_session(self, temp_dir: Path):
        """Test loading non-existent session."""
        manager = SessionManager(temp_dir)
        
        session = manager.load_session("nonexistent-id")
        assert session is None
    
    def test_delete_session(self, temp_dir: Path):
        """Test session deletion."""
        manager = SessionManager(temp_dir)
        
        # Create and save session
        session = manager.create_session("Test", "test-model")
        manager.save_session(session)
        
        # Verify it exists
        session_file = manager.sessions_dir / f"{session.id}.json"
        assert session_file.exists()
        
        # Delete session
        success = manager.delete_session(session.id)
        assert success
        assert not session_file.exists()
    
    def test_delete_nonexistent_session(self, temp_dir: Path):
        """Test deleting non-existent session."""
        manager = SessionManager(temp_dir)
        
        success = manager.delete_session("nonexistent-id")
        assert not success
    
    def test_list_sessions(self, temp_dir: Path):
        """Test listing sessions."""
        manager = SessionManager(temp_dir)
        
        # Create multiple sessions
        session1 = manager.create_session("Session 1", "model1")
        session2 = manager.create_session("Session 2", "model2")
        session3 = manager.create_session("Session 3", "model1")
        
        manager.save_session(session1)
        manager.save_session(session2)
        manager.save_session(session3)
        
        # List all sessions
        sessions = manager.list_sessions()
        assert len(sessions) == 3
        
        # List sessions by model
        model1_sessions = manager.list_sessions(model="model1")
        assert len(model1_sessions) == 2
        
        # List recent sessions
        recent_sessions = manager.list_sessions(limit=2)
        assert len(recent_sessions) == 2
    
    def test_list_sessions_sorted(self, temp_dir: Path):
        """Test session listing is sorted by last accessed."""
        manager = SessionManager(temp_dir)
        
        # Create sessions with different access times
        import time
        
        session1 = manager.create_session("Old Session", "test-model")
        manager.save_session(session1)
        
        time.sleep(0.1)  # Small delay
        
        session2 = manager.create_session("New Session", "test-model")
        manager.save_session(session2)
        
        sessions = manager.list_sessions()
        
        # Should be sorted by last_accessed (newest first)
        assert sessions[0].id == session2.id
        assert sessions[1].id == session1.id
    
    def test_cleanup_old_sessions(self, temp_dir: Path):
        """Test cleaning up old sessions."""
        manager = SessionManager(temp_dir)
        
        # Create multiple sessions
        sessions = []
        for i in range(5):
            session = manager.create_session(f"Session {i}", "test-model")
            manager.save_session(session)
            sessions.append(session)
        
        # Cleanup keeping only 3 most recent
        cleaned = manager.cleanup_old_sessions(keep_recent=3)
        
        assert cleaned == 2  # Should have removed 2 sessions
        
        remaining_sessions = manager.list_sessions()
        assert len(remaining_sessions) == 3
    
    def test_session_metadata(self, temp_dir: Path):
        """Test session metadata handling."""
        manager = SessionManager(temp_dir)
        
        session = manager.create_session("Test", "test-model")
        
        # Add metadata
        session.metadata = SessionMetadata(
            project_path="/test/project",
            git_branch="main",
            git_commit="abc123",
            custom_data={"test_key": "test_value"}
        )
        
        manager.save_session(session)
        
        # Load and verify metadata
        loaded = manager.load_session(session.id)
        assert loaded.metadata is not None
        assert loaded.metadata.project_path == "/test/project"
        assert loaded.metadata.git_branch == "main"
        assert loaded.metadata.custom_data["test_key"] == "test_value"
    
    def test_session_stats(self, temp_dir: Path):
        """Test session statistics."""
        manager = SessionManager(temp_dir)
        
        # Create sessions with different characteristics
        session1 = manager.create_session("Short", "model1")
        session1.add_message("user", "Hi")
        session1.add_message("assistant", "Hello")
        
        session2 = manager.create_session("Long", "model2")
        for i in range(10):
            session2.add_message("user", f"Message {i}")
            session2.add_message("assistant", f"Response {i}")
        
        manager.save_session(session1)
        manager.save_session(session2)
        
        stats = manager.get_session_stats()
        
        assert stats["total_sessions"] == 2
        assert stats["total_messages"] == 22  # 2 + 20
        assert "model1" in stats["models_used"]
        assert "model2" in stats["models_used"]
        assert stats["models_used"]["model1"] == 1
        assert stats["models_used"]["model2"] == 1


@pytest.mark.unit
class TestConversationHistory:
    """Test conversation history utilities."""
    
    def test_conversation_history_creation(self):
        """Test conversation history creation."""
        history = ConversationHistory()
        assert len(history.messages) == 0
    
    def test_add_messages(self):
        """Test adding messages to history."""
        history = ConversationHistory()
        
        history.add_user_message("Hello")
        history.add_assistant_message("Hi there!")
        history.add_system_message("System message")
        
        assert len(history.messages) == 3
        assert history.messages[0]["role"] == "user"
        assert history.messages[1]["role"] == "assistant"
        assert history.messages[2]["role"] == "system"
    
    def test_get_messages_for_api(self):
        """Test getting messages in API format."""
        history = ConversationHistory()
        
        history.add_user_message("Hello")
        history.add_assistant_message("Hi!")
        
        api_messages = history.get_messages_for_api()
        
        assert len(api_messages) == 2
        assert all("role" in msg and "content" in msg for msg in api_messages)
    
    def test_trim_history(self):
        """Test trimming history to limit."""
        history = ConversationHistory()
        
        # Add many messages
        for i in range(10):
            history.add_user_message(f"Message {i}")
            history.add_assistant_message(f"Response {i}")
        
        # Trim to last 6 messages
        history.trim_to_limit(6)
        
        assert len(history.messages) == 6
        # Should keep most recent messages
        assert "Message 7" in history.messages[-2]["content"]
    
    def test_estimate_tokens(self):
        """Test token estimation."""
        history = ConversationHistory()
        
        history.add_user_message("Hello world")
        history.add_assistant_message("Hi there, how are you?")
        
        # Simple estimation based on word count
        tokens = history.estimate_tokens()
        assert tokens > 0
        assert tokens < 100  # Should be reasonable for short messages
    
    def test_clear_history(self):
        """Test clearing history."""
        history = ConversationHistory()
        
        history.add_user_message("Hello")
        history.add_assistant_message("Hi!")
        
        assert len(history.messages) == 2
        
        history.clear()
        assert len(history.messages) == 0


@pytest.mark.unit 
class TestSessionMetadata:
    """Test session metadata handling."""
    
    def test_metadata_creation(self):
        """Test metadata creation."""
        metadata = SessionMetadata(
            project_path="/test/project",
            git_branch="feature-branch",
            git_commit="abc123def456",
            custom_data={"setting1": "value1"}
        )
        
        assert metadata.project_path == "/test/project"
        assert metadata.git_branch == "feature-branch"
        assert metadata.git_commit == "abc123def456"
        assert metadata.custom_data["setting1"] == "value1"
    
    def test_metadata_to_dict(self):
        """Test metadata serialization."""
        metadata = SessionMetadata(
            project_path="/test",
            custom_data={"key": "value"}
        )
        
        data = metadata.to_dict()
        
        assert data["project_path"] == "/test"
        assert data["custom_data"]["key"] == "value"
    
    def test_metadata_from_dict(self):
        """Test metadata deserialization."""
        data = {
            "project_path": "/test",
            "git_branch": "main",
            "custom_data": {"key": "value"}
        }
        
        metadata = SessionMetadata.from_dict(data)
        
        assert metadata.project_path == "/test"
        assert metadata.git_branch == "main"
        assert metadata.custom_data["key"] == "value"