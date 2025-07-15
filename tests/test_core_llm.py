"""
Tests for vagents.core.llm module.
"""
import pytest
import asyncio
import aiohttp
from unittest.mock import AsyncMock, MagicMock, patch
from vagents.core.llm import LLM
from vagents.core.protocol import Message


class TestLLM:
    """Test the LLM class."""

    def test_llm_initialization(self):
        """Test LLM initialization with basic parameters."""
        llm = LLM(
            model_name="test-model", base_url="https://api.test.com", api_key="test-key"
        )

        assert llm.model_name == "test-model"
        assert llm.base_url == "https://api.test.com"
        assert llm.api_key == "test-key"
        assert llm.default_model == "test-model"
        assert llm._session is None

    @pytest.mark.asyncio
    async def test_get_session_creates_new_session(self):
        """Test that _get_session creates a new aiohttp session."""
        llm = LLM(
            model_name="test-model", base_url="https://api.test.com", api_key="test-key"
        )

        session = await llm._get_session()

        assert isinstance(session, aiohttp.ClientSession)
        assert llm._session is session

        # Clean up
        await session.close()

    @pytest.mark.asyncio
    async def test_get_session_reuses_existing_session(self):
        """Test that _get_session reuses existing session."""
        llm = LLM(
            model_name="test-model", base_url="https://api.test.com", api_key="test-key"
        )

        session1 = await llm._get_session()
        session2 = await llm._get_session()

        assert session1 is session2

        # Clean up
        await session1.close()

    @pytest.mark.asyncio
    async def test_get_session_creates_new_when_closed(self):
        """Test that _get_session creates new session when previous is closed."""
        llm = LLM(
            model_name="test-model", base_url="https://api.test.com", api_key="test-key"
        )

        session1 = await llm._get_session()
        await session1.close()

        session2 = await llm._get_session()

        assert session1 is not session2
        assert isinstance(session2, aiohttp.ClientSession)

        # Clean up
        await session2.close()

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.post")
    async def test_call_success(self, mock_post):
        """Test successful text generation."""
        # Mock successful response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Generated text response"}}]
        }
        mock_post.return_value.__aenter__.return_value = mock_response

        llm = LLM(
            model_name="test-model", base_url="https://api.test.com", api_key="test-key"
        )

        messages = [Message(role="user", content="Test prompt")]
        result = await llm(messages)

        assert result == "Generated text response"
        mock_post.assert_called_once()

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.post")
    async def test_call_with_messages(self, mock_post):
        """Test text generation with message history."""
        # Mock successful response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Response to conversation"}}]
        }
        mock_post.return_value.__aenter__.return_value = mock_response

        llm = LLM(
            model_name="test-model", base_url="https://api.test.com", api_key="test-key"
        )

        messages = [
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi there!"),
            Message(role="user", content="Continue conversation"),
        ]

        result = await llm(messages)

        assert result == "Response to conversation"
        mock_post.assert_called_once()

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.post")
    async def test_call_http_error(self, mock_post):
        """Test handling of HTTP errors during generation."""
        # Mock error response
        mock_response = AsyncMock()
        mock_response.status = 500
        mock_response.text.return_value = "Internal Server Error"
        mock_post.return_value.__aenter__.return_value = mock_response

        llm = LLM(
            model_name="test-model", base_url="https://api.test.com", api_key="test-key"
        )

        messages = [Message(role="user", content="Test prompt")]
        with pytest.raises(Exception):
            await llm(messages)

    @pytest.mark.asyncio
    @patch("aiohttp.ClientSession.post")
    async def test_call_with_tools(self, mock_post):
        """Test text generation with tools parameter."""
        # Mock successful response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"tool_calls": [{"name": "test_tool"}]}}]
        }
        mock_post.return_value.__aenter__.return_value = mock_response

        llm = LLM(
            model_name="test-model", base_url="https://api.test.com", api_key="test-key"
        )

        tools = [{"type": "function", "function": {"name": "test_tool"}}]
        messages = [Message(role="user", content="Test prompt")]

        result = await llm(messages, tools=tools)

        # When tools are provided, the result is a generator, consume it to trigger HTTP call
        assert hasattr(result, "__aiter__")
        tool_calls = None
        async for chunk in result:
            tool_calls = chunk
            break

        assert tool_calls == [{"name": "test_tool"}]
        mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_closes_session(self):
        """Test that close properly closes the session."""
        llm = LLM(
            model_name="test-model", base_url="https://api.test.com", api_key="test-key"
        )

        # Create session
        session = await llm._get_session()
        assert not session.closed

        # Close should close session
        await llm.close()

        assert session.closed

    @pytest.mark.asyncio
    async def test_close_with_no_session(self):
        """Test that close works when no session exists."""
        llm = LLM(
            model_name="test-model", base_url="https://api.test.com", api_key="test-key"
        )

        # Should not raise any exception
        await llm.close()

        assert llm._session is None

    def test_model_name_property(self):
        """Test model_name property access."""
        llm = LLM(
            model_name="gpt-4", base_url="https://api.openai.com", api_key="sk-test"
        )

        assert llm.model_name == "gpt-4"
        assert llm.default_model == "gpt-4"

    @pytest.mark.asyncio
    @patch("vagents.core.llm.LLM._async_call_chat")
    async def test_backoff_on_rate_limit(self, mock_async_call):
        """Test backoff behavior on rate limit errors."""
        from aiohttp import ClientError

        # Counter to track calls
        call_count = 0

        async def mock_generator(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call raises a rate limit error
                raise ClientError("Rate limit exceeded")
            else:
                # Second call succeeds
                yield "Success after retry"

        mock_async_call.side_effect = mock_generator

        llm = LLM(
            model_name="test-model", base_url="https://api.test.com", api_key="test-key"
        )

        messages = [Message(role="user", content="Test prompt")]

        # Should retry and eventually succeed
        result = await llm(messages)

        assert result == "Success after retry"
        assert call_count == 2
