import os
import pytest


@pytest.fixture(autouse=True)
def _enable_fast_lm(monkeypatch):
    # Default all tests to use the fake LM fast path unless explicitly marked 'api'
    if os.environ.get("VAGENTS_LM_FAKE") is None:
        monkeypatch.setenv("VAGENTS_LM_FAKE", "1")
    yield
