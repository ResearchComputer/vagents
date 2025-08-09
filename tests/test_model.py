import asyncio

import pytest

from vagents.core.model import LM


@pytest.mark.asyncio
async def test_lm_invocation_monkeypatched(monkeypatch):
    monkeypatch.setenv("VAGENTS_LM_FAKE", "1")

    async def fake_request(self, *args, **kwargs):
        # mimic OpenAI-like response
        return {
            "choices": [
                {"message": {"content": "hello"}},
            ]
        }

    monkeypatch.setattr(LM, "_request", fake_request, raising=True)
    lm = LM(name="test-model", base_url="http://localhost", api_key="x")
    res = await lm(messages=[{"role": "user", "content": "hi"}])
    # In fake mode, content starts with [FAKE:<model>]
    assert "choices" in res and "message" in res["choices"][0]
