"""
Tests for vagents.core.session module.
"""
import pytest
from vagents.core.session import Session
from vagents.core.protocol import Message


class TestSession:
    """Test the Session class."""

    def test_session_initialization(self):
        """Test Session initialization."""
        session = Session("test_session_123")

        assert session.session_id == "test_session_123"
        assert session.history == []
        assert len(session.history) == 0

    def test_append_message_object(self):
        """Test appending a Message object to history."""
        session = Session("test_session")
        message = Message(role="user", content="Hello, world!")

        session.append(message)

        assert len(session.history) == 1
        assert session.history[0] == message
        assert session.history[0].role.value == "user"
        assert session.history[0].content == "Hello, world!"

    def test_append_message_dict(self):
        """Test appending a dictionary to history."""
        session = Session("test_session")
        message_dict = {"role": "assistant", "content": "Hello back!"}

        session.append(message_dict)

        assert len(session.history) == 1
        assert isinstance(session.history[0], Message)
        assert session.history[0].role.value == "assistant"
        assert session.history[0].content == "Hello back!"

    def test_append_message_list(self):
        """Test appending a list of messages to history."""
        session = Session("test_session")
        messages = [
            Message(role="user", content="First message"),
            Message(role="assistant", content="Second message"),
            {"role": "user", "content": "Third message"},
        ]

        session.append(messages)

        assert len(session.history) == 3
        assert session.history[0].role.value == "user"
        assert session.history[0].content == "First message"
        assert session.history[1].role.value == "assistant"
        assert session.history[1].content == "Second message"
        assert session.history[2].role.value == "user"
        assert session.history[2].content == "Third message"

    def test_clear_history(self):
        """Test clearing session history."""
        session = Session("test_session")

        # Add some messages
        session.append(Message(role="user", content="Message 1"))
        session.append(Message(role="assistant", content="Message 2"))
        assert len(session.history) == 2

        # Clear history
        session.clear()

        assert len(session.history) == 0
        assert session.history == []

    def test_repr_empty_session(self):
        """Test string representation of empty session."""
        session = Session("empty_session")

        repr_str = repr(session)

        assert "empty_session" in repr_str
        assert "-----" in repr_str

    def test_repr_with_messages(self):
        """Test Session string representation with messages."""
        session = Session("chat_session")
        session.append(Message(role="user", content="Hello"))
        session.append(Message(role="assistant", content="Hi!"))

        repr_str = repr(session)

        assert "chat_session" in repr_str
        assert "[MessageRole.USER]: Hello" in repr_str
        assert "[MessageRole.ASSISTANT]: Hi!" in repr_str

    def test_session_message_roles(self):
        """Test that different message roles are handled correctly."""
        session = Session("test_roles")

        # Add messages with different roles
        session.append(Message(role="system", content="System prompt"))
        session.append(Message(role="user", content="User question"))
        session.append(Message(role="assistant", content="Assistant response"))

        assert len(session.history) == 3
        assert session.history[0].role.value == "system"
        assert session.history[1].role.value == "user"
        assert session.history[2].role.value == "assistant"
