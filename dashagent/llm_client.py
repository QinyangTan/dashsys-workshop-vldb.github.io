from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

import requests

from .trajectory import compact_preview, redact_secrets


DEFAULT_OPENAI_MODEL = "gpt-4o-mini"


class LLMClient:
    def available(self) -> bool:
        raise NotImplementedError

    def provider_name(self) -> str:
        raise NotImplementedError

    def model_name(self) -> str:
        raise NotImplementedError

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        raise NotImplementedError


@dataclass
class NoOpLLMClient(LLMClient):
    reason: str = "OPENAI_API_KEY is not set"
    model: str = DEFAULT_OPENAI_MODEL

    def available(self) -> bool:
        return False

    def provider_name(self) -> str:
        return "none"

    def model_name(self) -> str:
        return self.model

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        return {
            "ok": False,
            "skipped": True,
            "reason": self.reason,
            "provider": self.provider_name(),
            "model": self.model_name(),
            "content": "",
        }


class OpenAILLMClient(LLMClient):
    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: int = 60,
    ) -> None:
        self.api_key = api_key if api_key is not None else os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
        self.timeout_seconds = timeout_seconds
        self.endpoint = os.getenv("OPENAI_CHAT_COMPLETIONS_URL", "https://api.openai.com/v1/chat/completions")

    def available(self) -> bool:
        return bool(self.api_key)

    def provider_name(self) -> str:
        return "openai" if self.available() else "none"

    def model_name(self) -> str:
        return self.model

    def generate(
        self,
        system_prompt: str,
        user_prompt: str,
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        if not self.available():
            return NoOpLLMClient(model=self.model).generate(system_prompt, user_prompt, tools)
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0,
        }
        if tools:
            payload["tools"] = tools
        try:
            response = requests.post(
                self.endpoint,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                data=json.dumps(payload),
                timeout=self.timeout_seconds,
            )
            body = response.json()
        except Exception as exc:
            return {
                "ok": False,
                "skipped": False,
                "provider": self.provider_name(),
                "model": self.model_name(),
                "content": "",
                "error": str(exc)[:500],
            }
        content = ""
        tool_calls: list[dict[str, Any]] = []
        try:
            message = body["choices"][0]["message"]
            content = message.get("content") or ""
            for raw_call in message.get("tool_calls") or []:
                function = raw_call.get("function") or {}
                arguments = function.get("arguments") or {}
                if isinstance(arguments, str):
                    try:
                        arguments = json.loads(arguments)
                    except Exception:
                        arguments = {"_raw": arguments}
                tool_calls.append(
                    {
                        "id": raw_call.get("id"),
                        "type": raw_call.get("type"),
                        "tool": function.get("name"),
                        "arguments": arguments if isinstance(arguments, dict) else {},
                    }
                )
        except Exception:
            content = ""
        return redact_secrets(
            {
                "ok": response.ok,
                "skipped": False,
                "provider": self.provider_name(),
                "model": self.model_name(),
                "content": content,
                "tool_calls": tool_calls,
                "usage": body.get("usage", {}),
                "raw_preview": compact_preview(body, 1200),
                "error": None if response.ok else str(body)[:500],
            }
        )


def get_llm_client() -> LLMClient:
    client = OpenAILLMClient()
    if client.available():
        return client
    return NoOpLLMClient(model=client.model_name())
