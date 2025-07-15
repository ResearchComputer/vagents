"""
Tests for vagents.core.protocol module.
"""
import pytest
from vagents.core.protocol import Message, MessageRole, ActionOutput, ActionOutputStatus


class TestMessage:
    """Test the Message class."""

    def test_message_basic_creation(self):
        """Test basic Message creation."""
        message = Message(role="user", content="Hello, world!")

        assert message.role == MessageRole.USER
        assert message.content == "Hello, world!"

    def test_message_with_role_enum(self):
        """Test Message creation with MessageRole enum."""
        message = Message(role=MessageRole.ASSISTANT, content="Hi there!")

        assert message.role == MessageRole.ASSISTANT
        assert message.content == "Hi there!"

    def test_message_to_dict(self):
        """Test Message to_dict method."""
        message = Message(role="user", content="Test")
        result = message.to_dict()

        assert result == {"role": "user", "content": "Test"}

    def test_message_validation_role(self):
        """Test Message validation with invalid role."""
        # Should work fine with valid role
        message = Message(role="system", content="System message")
        assert message.role == MessageRole.SYSTEM


class TestMessageRole:
    """Test the MessageRole enum."""

    def test_message_role_values(self):
        """Test MessageRole enum values."""
        assert MessageRole.USER == "user"
        assert MessageRole.ASSISTANT == "assistant"
        assert MessageRole.SYSTEM == "system"
        assert MessageRole.TOOL_CALL == "tool-call"
        assert MessageRole.AGENT == "agent"
        assert MessageRole.TOOL_RESPONSE == "tool-response"

    def test_message_role_roles_method(self):
        """Test MessageRole.roles() class method."""
        roles = MessageRole.roles()
        expected = [
            "user",
            "assistant",
            "system",
            "tool-call",
            "agent",
            "tool-response",
        ]
        assert roles == expected

    def test_message_role_from_str(self):
        """Test MessageRole.from_str() class method."""
        assert MessageRole.from_str("user") == MessageRole.USER
        assert MessageRole.from_str("assistant") == MessageRole.ASSISTANT
        assert MessageRole.from_str("invalid") == MessageRole.USER  # defaults to user


class TestActionOutput:
    """Test the ActionOutput class."""

    def test_action_output_creation(self):
        """Test ActionOutput creation."""
        output = ActionOutput(content="Test content")

        assert output.status == ActionOutputStatus.NORMAL
        assert output.content == "Test content"

    def test_action_output_with_dict_content(self):
        """Test ActionOutput with dict content."""
        content = {"key": "value", "number": 42}
        output = ActionOutput(content=content, status=ActionOutputStatus.ABNORMAL)

        assert output.status == ActionOutputStatus.ABNORMAL
        assert output.content == content

    def test_action_output_cancelled_status(self):
        """Test ActionOutput with cancelled status."""
        output = ActionOutput(status=ActionOutputStatus.CANCELLED, content="Cancelled")

        assert output.status == ActionOutputStatus.CANCELLED
        assert output.content == "Cancelled"


class TestActionOutputStatus:
    """Test the ActionOutputStatus enum."""

    def test_action_output_status_values(self):
        """Test ActionOutputStatus enum values."""
        assert ActionOutputStatus.NORMAL == "normal"
        assert ActionOutputStatus.ABNORMAL == "abnormal"
        assert ActionOutputStatus.CANCELLED == "cancelled"
        assert ActionOutputStatus.AGENT_CONTEXT_LIMIT == "agent context limit"


class TestMessageIntegration:
    """Test Message integration scenarios."""

    def test_conversation_flow(self):
        """Test a typical conversation flow."""
        messages = [
            Message(role=MessageRole.SYSTEM, content="You are a helpful assistant."),
            Message(role=MessageRole.USER, content="What is Python?"),
            Message(
                role=MessageRole.ASSISTANT, content="Python is a programming language."
            ),
            Message(role=MessageRole.USER, content="Tell me more about it."),
        ]

        assert len(messages) == 4
        assert messages[0].role == MessageRole.SYSTEM
        assert messages[1].role == MessageRole.USER
        assert messages[2].role == MessageRole.ASSISTANT
        assert messages[3].role == MessageRole.USER

    def test_message_serialization(self):
        """Test message serialization to dict."""
        message = Message(role=MessageRole.USER, content="Test")
        serialized = message.to_dict()

        assert "role" in serialized
        assert "content" in serialized
        assert serialized["role"] == "user"
        assert serialized["content"] == "Test"
