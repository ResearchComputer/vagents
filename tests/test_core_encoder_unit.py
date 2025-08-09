import builtins
import pytest

from vagents.core.encoder import TextEncoder


def test_textencoder_importerror_when_missing_dependency(monkeypatch):
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name.startswith("sentence_transformers"):
            raise ImportError("no sentence-transformers")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    with pytest.raises(ImportError) as ei:
        _ = TextEncoder("all-MiniLM-L6-v2")
    assert "sentence-transformers" in str(ei.value)
