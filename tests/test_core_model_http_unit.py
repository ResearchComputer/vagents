import pytest

import types

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
