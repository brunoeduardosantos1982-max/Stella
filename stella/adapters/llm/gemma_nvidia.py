from typing import Any

from openai import OpenAI

from stella.adapters.llm.base import LLMProvider, LLMResponse, Message

_NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
_MODELO = "google/gemma-4-31b-it"


class GemmaNvidiaProvider(LLMProvider):
    """Provedor LLM usando Gemma 4 31B IT via NVIDIA NIM (API OpenAI-compatible).

    O parâmetro `client` permite injetar um dublê nos testes.
    """

    def __init__(self, api_key: str, client: Any = None) -> None:
        self._client = client or OpenAI(
            base_url=_NVIDIA_BASE_URL,
            api_key=api_key,
        )

    def complete(self, prompt: str) -> LLMResponse:
        return self.chat([Message(role="user", content=prompt)])

    def chat(self, messages: list[Message]) -> LLMResponse:
        payload = [{"role": m.role, "content": m.content} for m in messages]
        resp = self._client.chat.completions.create(
            model=_MODELO,
            messages=payload,
        )
        return LLMResponse(
            texto=resp.choices[0].message.content,
            tokens_input=resp.usage.prompt_tokens,
            tokens_output=resp.usage.completion_tokens,
        )
