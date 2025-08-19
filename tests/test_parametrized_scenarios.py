import pytest
import asyncio
from unittest.mock import patch
from vagents.core.model import LM


class TestLMParametrized:
    """Parametrized tests for LM model to cover multiple scenarios efficiently"""
    
    @pytest.mark.parametrize("fake_mode", ["0", "1", "true", "false", "yes", "no"])
    @pytest.mark.asyncio
    async def test_lm_fake_mode_variations(self, monkeypatch, fake_mode):
        """Test LM with different fake mode environment variable values"""
        monkeypatch.setenv("VAGENTS_LM_FAKE", fake_mode)
        
        lm = LM(name="test-model")
        messages = [{"role": "user", "content": "test message"}]
        
        if fake_mode.lower() in {"1", "true", "yes"}:
            # Should use fake mode
            result = await lm(messages=messages)
            assert "choices" in result
            assert "[FAKE:test-model]" in result["choices"][0]["message"]["content"]
        else:
            # Should try real HTTP request (will fail in test environment)
            # We'll just check it doesn't crash during initialization
            assert lm.name == "test-model"
    
    @pytest.mark.parametrize("message_content", [
        "Simple text",
        "",  # Empty content
        "A" * 300,  # Long content (>200 chars)
        "Text with émojis 🎉🚀✨",
        "Multiline\ntext\nwith\nbreaks",
        "Text with\ttabs and    spaces",
        "Special chars: !@#$%^&*()[]{}|\\:;\"'<>?,./",
        "中文测试内容",  # Chinese characters
        "🎯 Mixed content with numbers 123 and symbols @#$"
    ])
    @pytest.mark.asyncio
    async def test_lm_fake_mode_content_variations(self, monkeypatch, message_content):
        """Test LM fake mode with various message content types"""
        monkeypatch.setenv("VAGENTS_LM_FAKE", "1")
        
        lm = LM(name="content-test")
        messages = [{"role": "user", "content": message_content}]
        
        result = await lm(messages=messages)
        
        assert "choices" in result
        response_content = result["choices"][0]["message"]["content"]
        assert "[FAKE:content-test]" in response_content
        
        if message_content.strip():
            # Non-empty content should be included (possibly truncated)
            content_in_response = message_content[:200] if len(message_content) > 200 else message_content
            if content_in_response.strip():
                assert content_in_response.strip() in response_content
        else:
            # Empty content should result in "OK"
            assert "OK" in response_content
    
    @pytest.mark.parametrize("message_structure", [
        [{"role": "user", "content": "test"}],
        [{"role": "system", "content": "system"}, {"role": "user", "content": "user"}],
        [{"role": "user", "content": "first"}, {"role": "assistant", "content": "response"}, {"role": "user", "content": "second"}],
        [],  # Empty messages
        [{"role": "system", "content": "only system"}],  # No user messages
        [{"role": "assistant", "content": "only assistant"}],  # No user messages
    ])
    @pytest.mark.asyncio
    async def test_lm_fake_mode_message_structures(self, monkeypatch, message_structure):
        """Test LM fake mode with different message structures"""
        monkeypatch.setenv("VAGENTS_LM_FAKE", "1")
        
        lm = LM(name="structure-test")
        
        result = await lm(messages=message_structure)
        
        assert "choices" in result
        response_content = result["choices"][0]["message"]["content"]
        assert "[FAKE:structure-test]" in response_content
        
        # Find last user message if any
        last_user_content = None
        for msg in reversed(message_structure):
            if isinstance(msg, dict) and msg.get("role") == "user":
                last_user_content = msg.get("content", "")
                break
        
        if last_user_content and last_user_content.strip():
            truncated_content = last_user_content[:200] if len(last_user_content) > 200 else last_user_content
            assert truncated_content.strip() in response_content
        else:
            assert "OK" in response_content
    
    @pytest.mark.parametrize("multimodal_content", [
        [{"type": "text", "text": "Describe image"}],
        [{"type": "text", "text": "First part"}, {"type": "text", "text": "Second part"}],
        [{"type": "text", "text": "Text"}, {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}}],
        [{"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}}],  # No text parts
        [],  # Empty content array
    ])
    @pytest.mark.asyncio
    async def test_lm_fake_mode_multimodal_content(self, monkeypatch, multimodal_content):
        """Test LM fake mode with different multimodal content structures"""
        monkeypatch.setenv("VAGENTS_LM_FAKE", "1")
        
        lm = LM(name="multimodal-test")
        messages = [{"role": "user", "content": multimodal_content}]
        
        result = await lm(messages=messages)
        
        assert "choices" in result
        response_content = result["choices"][0]["message"]["content"]
        assert "[FAKE:multimodal-test]" in response_content
        
        # Extract text parts
        text_parts = [
            part.get("text", "")
            for part in multimodal_content
            if isinstance(part, dict) and part.get("type") == "text"
        ]
        
        if text_parts and any(part.strip() for part in text_parts):
            combined_text = "\n".join(text_parts)
            truncated_text = combined_text[:200] if len(combined_text) > 200 else combined_text
            if truncated_text.strip():
                assert truncated_text.strip() in response_content
        else:
            assert "OK" in response_content
    
    @pytest.mark.parametrize("lm_kwargs,expected_filtered", [
        ({"temperature": 0.7}, {"temperature": 0.7}),
        ({"temperature": 0.7, "max_tokens": 100}, {"temperature": 0.7, "max_tokens": 100}),
        ({"temperature": 0.7, "invalid_param": "value"}, {"temperature": 0.7}),
        ({"invalid_param": "value", "another_invalid": 123}, {}),
        ({"temperature": 0.7, "top_p": 0.9, "max_tokens": 100, "stream": False}, 
         {"temperature": 0.7, "top_p": 0.9, "max_tokens": 100, "stream": False}),
        ({}, {}),
    ])
    @pytest.mark.asyncio
    async def test_lm_invoke_parameter_filtering(self, monkeypatch, lm_kwargs, expected_filtered):
        """Test LM invoke method filters parameters correctly"""
        monkeypatch.setenv("VAGENTS_LM_FAKE", "1")
        
        # Track what parameters were actually passed to _request
        captured_kwargs = {}
        
        async def mock_request(*args, **kwargs):
            captured_kwargs.update(kwargs)
            return {"choices": [{"message": {"content": "test response"}}]}
        
        lm = LM(name="param-test")
        
        def make_messages(text):
            return [{"role": "user", "content": text}]
        
        with patch.object(lm, '_request', side_effect=mock_request):
            await lm.invoke(make_messages, "test prompt", **lm_kwargs)
        
        # Check that only valid LM parameters were passed
        for key, value in expected_filtered.items():
            assert key in captured_kwargs
            assert captured_kwargs[key] == value
        
        # Check that invalid parameters were filtered out
        for key in lm_kwargs:
            if key not in expected_filtered:
                assert key not in captured_kwargs
    
    @pytest.mark.parametrize("model_name", [
        "simple-model",
        "model/with/slashes",
        "model-with-dashes",
        "model_with_underscores",
        "Model.With.Dots",
        "123-numeric-model",
        "🤖-emoji-model",
        "",  # Empty name
    ])
    def test_lm_initialization_with_different_names(self, model_name):
        """Test LM initialization with various model names"""
        lm = LM(name=model_name)
        assert lm.name == model_name
        assert isinstance(lm._headers, dict)
        assert "Authorization" in lm._headers
        assert "Content-Type" in lm._headers
        assert "User-Agent" in lm._headers
    
    @pytest.mark.parametrize("base_url,api_key", [
        ("https://api.example.com", "key123"),
        ("http://localhost:8000", "local-key"),
        ("https://api.openai.com/v1", "sk-..."),
        ("", "empty-url-key"),  # Empty URL
        ("https://api.example.com", ""),  # Empty key
        ("ftp://invalid.protocol.com", "key"),  # Invalid protocol
    ])
    def test_lm_initialization_with_different_urls_and_keys(self, base_url, api_key):
        """Test LM initialization with various URLs and API keys"""
        lm = LM(name="test-model", base_url=base_url, api_key=api_key)
        
        assert lm.base_url == base_url
        assert lm.api_key == api_key
        assert lm._headers["Authorization"] == f"Bearer {api_key}"
        assert lm._headers["Content-Type"] == "application/json"
        assert lm._headers["User-Agent"] == "vagents/1.0"
    
    @pytest.mark.parametrize("concurrent_count", [1, 2, 5, 10])
    @pytest.mark.asyncio
    async def test_lm_concurrent_requests(self, monkeypatch, concurrent_count):
        """Test LM handles concurrent requests properly"""
        monkeypatch.setenv("VAGENTS_LM_FAKE", "1")
        
        lm = LM(name="concurrent-test")
        
        async def make_request(request_id):
            messages = [{"role": "user", "content": f"Request {request_id}"}]
            result = await lm(messages=messages)
            return request_id, result
        
        # Start concurrent requests
        tasks = [make_request(i) for i in range(concurrent_count)]
        results = await asyncio.gather(*tasks)
        
        # Verify all requests completed successfully
        assert len(results) == concurrent_count
        
        for request_id, result in results:
            assert "choices" in result
            response_content = result["choices"][0]["message"]["content"]
            assert "[FAKE:concurrent-test]" in response_content
            assert f"Request {request_id}" in response_content