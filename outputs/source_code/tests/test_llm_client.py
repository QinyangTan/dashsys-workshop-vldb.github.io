from __future__ import annotations

from dashagent.llm_client import NoOpLLMClient, OpenAILLMClient


def test_noop_llm_client_skips_without_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = NoOpLLMClient()
    result = client.generate("system", "user")
    assert not client.available()
    assert result["skipped"] is True
    assert result["reason"] == "OPENAI_API_KEY is not set"


def test_openai_client_unavailable_without_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    client = OpenAILLMClient()
    assert not client.available()
    assert client.provider_name() == "none"
    result = client.generate("system", "user")
    assert result["skipped"] is True
