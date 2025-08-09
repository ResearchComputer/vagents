import pytest

from vagents.core.model import LM


@pytest.mark.asyncio
async def test_lm_fake_offline_mode(monkeypatch):
    monkeypatch.setenv("VAGENTS_LM_FAKE", "1")
    lm = LM(name="fake-model")
    res = await lm(messages=[{"role": "user", "content": "hello world"}])
    assert "choices" in res
    assert "message" in res["choices"][0]
    assert "FAKE" in res["choices"][0]["message"]["content"]
