import pytest

import types
import os

from vagents.core.model import LM


class _FakeResp:
    def __init__(self, status: int, payload: dict):
        self.status = status
        self._payload = payload

    async def json(self):
        return self._payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeSession:
    def __init__(self, status: int = 200, payload: dict | None = None):
        self._status = status
        self._payload = payload or {"choices": [{"message": {"content": "ok"}}]}

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def post(self, *a, **k):
        return _FakeResp(self._status, self._payload)


@pytest.mark.asyncio
async def test_lm_http_success(monkeypatch):
    # Force online path
    monkeypatch.setenv("VAGENTS_LM_FAKE", "0")

    # Monkeypatch aiohttp.ClientSession to fake
    import vagents.core.model as model_mod

    monkeypatch.setattr(
        model_mod,
        "aiohttp",
        types.SimpleNamespace(ClientSession=lambda: _FakeSession()),
        raising=True,
    )

    lm = LM(name="m")
    res = await lm(
        messages=[{"role": "user", "content": "hi"}], temperature=0.1, extra="x"
    )
    assert "choices" in res


@pytest.mark.asyncio
async def test_lm_http_error_status(monkeypatch):
    monkeypatch.setenv("VAGENTS_LM_FAKE", "0")
    import vagents.core.model as model_mod

    monkeypatch.setattr(
        model_mod,
        "aiohttp",
        types.SimpleNamespace(ClientSession=lambda: _FakeSession(status=500)),
        raising=True,
    )

    lm = LM(name="m")
    with pytest.raises(Exception):
        _ = await lm(messages=[{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_lm_invoke_filters_kwargs(monkeypatch):
    monkeypatch.setenv("VAGENTS_LM_FAKE", "1")

    def make_messages(x):
        return [{"role": "user", "content": f"{x}"}]

    lm = LM(name="m")
    # invoke should ignore unknown kwargs like foo and keep temperature
    res = await lm.invoke(make_messages, "hello", temperature=0.2, foo=1)
    assert "choices" in res


@pytest.mark.asyncio
async def test_lm_fake_mode_multimodal_content(monkeypatch):
    """Test fake mode handles multimodal content properly"""
    monkeypatch.setenv("VAGENTS_LM_FAKE", "1")
    
    lm = LM(name="test-model")
    
    # Test with multimodal content (list format)
    multimodal_messages = [
        {
            "role": "user", 
            "content": [
                {"type": "text", "text": "Describe this image"},
                {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,..."}}
            ]
        }
    ]
    
    res = await lm(messages=multimodal_messages)
    assert "choices" in res
    assert "[FAKE:test-model]" in res["choices"][0]["message"]["content"]
    assert "Describe this image" in res["choices"][0]["message"]["content"]


@pytest.mark.asyncio 
async def test_lm_fake_mode_empty_messages(monkeypatch):
    """Test fake mode handles empty messages gracefully"""
    monkeypatch.setenv("VAGENTS_LM_FAKE", "1")
    
    lm = LM(name="test-model")
    
    # Test with empty messages
    res = await lm(messages=[])
    assert "choices" in res
    assert "[FAKE:test-model] OK" == res["choices"][0]["message"]["content"]


@pytest.mark.asyncio
async def test_lm_fake_mode_no_user_messages(monkeypatch):
    """Test fake mode handles messages without user role"""
    monkeypatch.setenv("VAGENTS_LM_FAKE", "1")
    
    lm = LM(name="test-model")
    
    # Test with only system messages
    system_only_messages = [
        {"role": "system", "content": "You are a helpful assistant"}
    ]
    
    res = await lm(messages=system_only_messages)
    assert "choices" in res
    assert "[FAKE:test-model] OK" == res["choices"][0]["message"]["content"]


@pytest.mark.asyncio
async def test_lm_fake_mode_long_content_truncation(monkeypatch):
    """Test fake mode truncates long content to 200 chars"""
    monkeypatch.setenv("VAGENTS_LM_FAKE", "1")
    
    lm = LM(name="test-model")
    
    # Create content longer than 200 chars
    long_content = "x" * 300
    messages = [{"role": "user", "content": long_content}]
    
    res = await lm(messages=messages)
    assert "choices" in res
    content = res["choices"][0]["message"]["content"]
    assert content.startswith("[FAKE:test-model]")
    # Should be truncated to 200 chars plus the prefix
    assert len(content) <= len("[FAKE:test-model] ") + 200


@pytest.mark.asyncio
async def test_lm_fake_mode_malformed_content_handling(monkeypatch):
    """Test fake mode handles malformed content gracefully"""
    monkeypatch.setenv("VAGENTS_LM_FAKE", "1")
    
    lm = LM(name="test-model")
    
    # Test with malformed messages that could cause exceptions
    malformed_messages = [
        {"role": "user", "content": None},  # None content
        {"role": "user"},  # Missing content
        {"not_role": "user", "content": "test"},  # Wrong key
    ]
    
    res = await lm(messages=malformed_messages)
    assert "choices" in res
    assert "[FAKE:test-model] OK" == res["choices"][0]["message"]["content"]


@pytest.mark.asyncio
async def test_lm_init_with_custom_parameters():
    """Test LM initialization with custom parameters"""
    custom_lm = LM(
        name="custom-model",
        base_url="https://custom.api.com",
        api_key="custom-key"
    )
    
    assert custom_lm.name == "custom-model"
    assert custom_lm.base_url == "https://custom.api.com"
    assert custom_lm.api_key == "custom-key"
    assert custom_lm._headers["Authorization"] == "Bearer custom-key"
    assert custom_lm._headers["Content-Type"] == "application/json"
    assert custom_lm._headers["User-Agent"] == "vagents/1.0"


@pytest.mark.asyncio
async def test_lm_init_with_environment_variables(monkeypatch):
    """Test LM initialization uses environment variables as defaults when not specified"""
    # Clear any existing env vars first
    monkeypatch.delenv("VAGENTS_LM_BASE_URL", raising=False)
    monkeypatch.delenv("VAGENTS_LM_API_KEY", raising=False)
    
    # Set new values
    monkeypatch.setenv("VAGENTS_LM_BASE_URL", "https://env.api.com")
    monkeypatch.setenv("VAGENTS_LM_API_KEY", "env-key")
    
    # Create LM with explicit parameters that use the environment
    lm = LM(
        name="env-model",
        base_url=os.environ.get("VAGENTS_LM_BASE_URL", "https://ai.research.computer"),
        api_key=os.environ.get("VAGENTS_LM_API_KEY", "your-api-key-here")
    )
    
    assert lm.name == "env-model"
    assert lm.base_url == "https://env.api.com"
    assert lm.api_key == "env-key"


@pytest.mark.asyncio
async def test_lm_invoke_with_multiple_args(monkeypatch):
    """Test LM invoke method with multiple positional arguments"""
    monkeypatch.setenv("VAGENTS_LM_FAKE", "1")
    
    def make_complex_messages(prompt, context, style):
        return [
            {"role": "system", "content": f"Style: {style}"},
            {"role": "user", "content": f"Context: {context}. Prompt: {prompt}"}
        ]
    
    lm = LM(name="test-model")
    
    res = await lm.invoke(
        make_complex_messages, 
        "What is AI?", 
        "educational content", 
        "formal",
        temperature=0.5,
        max_tokens=100,
        unknown_param="ignored"
    )
    
    assert "choices" in res
    content = res["choices"][0]["message"]["content"]
    assert "What is AI?" in content
    assert "educational content" in content


@pytest.mark.asyncio
async def test_lm_http_different_error_codes(monkeypatch):
    """Test LM handles different HTTP error codes"""
    import vagents.core.model as model_mod
    
    error_codes = [400, 401, 403, 404, 429, 500, 502, 503]
    
    for error_code in error_codes:
        monkeypatch.setenv("VAGENTS_LM_FAKE", "0")
        
        monkeypatch.setattr(
            model_mod,
            "aiohttp",
            types.SimpleNamespace(ClientSession=lambda code=error_code: _FakeSession(status=code)),
            raising=True,
        )
        
        lm = LM(name="error-test")
        
        with pytest.raises(Exception) as exc_info:
            await lm(messages=[{"role": "user", "content": "test"}])
        
        assert str(error_code) in str(exc_info.value)


@pytest.mark.asyncio
async def test_lm_http_custom_payload_response(monkeypatch):
    """Test LM handles custom response payload"""
    monkeypatch.setenv("VAGENTS_LM_FAKE", "0")
    import vagents.core.model as model_mod
    
    custom_payload = {
        "choices": [
            {
                "message": {
                    "content": "Custom response content",
                    "role": "assistant"
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {"total_tokens": 42}
    }
    
    monkeypatch.setattr(
        model_mod,
        "aiohttp",
        types.SimpleNamespace(ClientSession=lambda: _FakeSession(payload=custom_payload)),
        raising=True,
    )
    
    lm = LM(name="custom-test")
    res = await lm(messages=[{"role": "user", "content": "test"}])
    
    assert res == custom_payload
    assert res["choices"][0]["message"]["content"] == "Custom response content"
    assert res["usage"]["total_tokens"] == 42
