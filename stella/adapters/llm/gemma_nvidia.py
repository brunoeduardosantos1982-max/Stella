from datetime import datetime
from typing import Any

import openai as openai_sdk
from openai import OpenAI

from stella.adapters.llm.base import (
    LLMAuthenticationError,
    LLMProvider,
    LLMProviderError,
    LLMRateLimitError,
    LLMResponse,
    LLMUnavailableError,
    Message,
)
from stella.infra.usage_tracker import UsageRecord, UsageTracker, estimar_custo

_NVIDIA_BASE_URL = "https://integrate.api.nvidia.com/v1"
_MODELO = "google/gemma-4-31b-it"


class GemmaNvidiaProvider(LLMProvider):
    """Provedor LLM usando Gemma 4 31B IT via NVIDIA NIM (API OpenAI-compatible).

    O parâmetro `client` permite injetar um dublê nos testes.
    """

    def __init__(
        self,
        api_key: str,
        client: Any = None,
        tracker: UsageTracker | None = None,
    ) -> None:
        self._client: Any = client or OpenAI(
            base_url=_NVIDIA_BASE_URL,
            api_key=api_key,
        )
        self._tracker = tracker

    def complete(self, prompt: str) -> LLMResponse:
        return self.chat([Message(role="user", content=prompt)])

    def chat(self, messages: list[Message]) -> LLMResponse:
        payload = [{"role": m.role, "content": m.content} for m in messages]
        try:
            resp = self._client.chat.completions.create(
                model=_MODELO,
                messages=payload,
            )
        except openai_sdk.RateLimitError as e:
            raise LLMRateLimitError(str(e)) from e
        except openai_sdk.AuthenticationError as e:
            raise LLMAuthenticationError(str(e)) from e
        except openai_sdk.APIConnectionError as e:
            raise LLMUnavailableError(str(e)) from e
        except openai_sdk.APIStatusError as e:
            raise LLMUnavailableError(f"{e.status_code}: {e.message}") from e
        except Exception as e:
            raise LLMProviderError(str(e)) from e
        result = LLMResponse(
            texto=resp.choices[0].message.content,
            tokens_input=resp.usage.prompt_tokens,
            tokens_output=resp.usage.completion_tokens,
        )
        if self._tracker is not None:
            self._tracker.record(
                UsageRecord(
                    momento=datetime.now(),
                    provider="gemma_nvidia",
                    modelo=_MODELO,
                    tokens_input=resp.usage.prompt_tokens,
                    tokens_output=resp.usage.completion_tokens,
                    custo_usd=estimar_custo(
                        _MODELO, resp.usage.prompt_tokens, resp.usage.completion_tokens
                    ),
                )
            )
        return result
