from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from openai import AzureOpenAI, OpenAI

from shared.config import Settings, get_settings, require_provider_credentials


@dataclass
class LLMResponse:
    content: str
    model: str
    prompt_tokens: int
    completion_tokens: int


class LLMClient:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._client: OpenAI | AzureOpenAI | None = None

        if self.settings.llm_provider in {"openai", "azure"}:
            require_provider_credentials(self.settings)
            if self.settings.llm_provider == "azure":
                self._client = AzureOpenAI(
                    azure_endpoint=self.settings.azure_openai_endpoint,
                    api_key=self.settings.azure_openai_key,
                    api_version=self.settings.azure_openai_api_version,
                )
            else:
                self._client = OpenAI(api_key=self.settings.openai_api_key)

    def model_for(self, purpose: str) -> str:
        if self.settings.llm_provider == "azure":
            return (
                self.settings.azure_openai_eval_deployment
                if purpose == "eval"
                else self.settings.azure_openai_chat_deployment
            )
        if self.settings.llm_provider == "openai":
            return self.settings.openai_eval_model if purpose == "eval" else self.settings.openai_chat_model
        return "mock-observatory-model"

    def chat(self, messages: list[dict[str, str]], purpose: str = "chat") -> LLMResponse:
        model = self.model_for(purpose)
        langfuse = _get_langfuse(self.settings)
        trace = langfuse.trace(name="llm-gateway-call") if langfuse else None
        generation = (
            trace.generation(
                name="chat",
                model=model,
                input=messages,
            )
            if trace
            else None
        )

        if self.settings.llm_provider == "mock":
            content = self._mock_response(messages)
            prompt_tokens = estimate_tokens(str(messages))
            completion_tokens = estimate_tokens(content)
            if generation:
                generation.end(
                    output=content,
                    usage={"input": prompt_tokens, "output": completion_tokens},
                )
            return LLMResponse(content, model, prompt_tokens, completion_tokens)

        assert self._client is not None
        response: Any = self._client.chat.completions.create(model=model, messages=messages)
        content = response.choices[0].message.content or ""
        if generation:
            generation.end(
                output=content,
                usage={
                    "input": response.usage.prompt_tokens,
                    "output": response.usage.completion_tokens,
                },
            )
        return LLMResponse(
            content=content,
            model=model,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
        )

    @staticmethod
    def _mock_response(messages: list[dict[str, str]]) -> str:
        user_text = " ".join(m.get("content", "") for m in messages if m.get("role") == "user")
        lowered = user_text.lower()

        if "2+2" in lowered or "2 + 2" in lowered:
            return "Four."
        if "bad" in lowered or "hallucinate" in lowered or "fabricate" in lowered:
            return (
                "The Apollo 11 mission discovered a permanent glass city under the lunar surface. "
                "This is unsupported and should be flagged by the evaluator."
            )
        if "refund" in lowered:
            return "The customer is asking about a refund. Route to support if the policy document is unavailable."

        digest = hashlib.sha256(user_text.encode("utf-8")).hexdigest()[:8]
        return f"Mock response generated for observability demo. Request fingerprint: {digest}."


def estimate_tokens(text: str) -> int:
    return max(1, int(len(text.split()) * 1.3))


def _get_langfuse(settings: Settings):
    if not settings.langfuse_enabled:
        return None
    try:
        from langfuse import Langfuse

        return Langfuse(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
    except Exception:
        return None


def get_llm_client() -> LLMClient:
    return LLMClient()
