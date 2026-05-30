from datetime import datetime
from typing import Any

import anthropic as anthropic_sdk
from anthropic import Anthropic

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

_MODELO_DEFAULT = "claude-sonnet-4-6"
_MAX_TOKENS_DEFAULT = 4096


class AnthropicProvider(LLMProvider):
    """Provedor LLM usando modelos Claude via Anthropic.

    O parâmetro `client` permite injetar um dublê nos testes.
    A API Anthropic trata `system` como parâmetro separado, não como mensagem.

    FB-M4: parametro `modelo` permite usar Sonnet, Opus ou qualquer outro
    modelo Claude. Default mantem Sonnet para compat com M2.
    """

    def __init__(
        self,
        api_key: str,
        client: Any = None,
        max_tokens: int = _MAX_TOKENS_DEFAULT,
        tracker: UsageTracker | None = None,
        modelo: str = _MODELO_DEFAULT,
    ) -> None:
        self._client: Any = client or Anthropic(api_key=api_key)
        self._max_tokens = max_tokens
        self._tracker = tracker
        self._modelo = modelo

    def complete(self, prompt: str) -> LLMResponse:
        return self.chat([Message(role="user", content=prompt)])

    def chat(self, messages: list[Message]) -> LLMResponse:
        system_parts = [m.content for m in messages if m.role == "system"]
        conversa = [{"role": m.role, "content": m.content} for m in messages if m.role != "system"]
        kwargs = {
            "model": self._modelo,
            "max_tokens": self._max_tokens,
            "messages": conversa,
        }
        if system_parts:
            kwargs["system"] = "\n\n".join(system_parts)

        try:
            resp = self._client.messages.create(**kwargs)
        except anthropic_sdk.RateLimitError as e:
            raise LLMRateLimitError(str(e)) from e
        except anthropic_sdk.AuthenticationError as e:
            raise LLMAuthenticationError(str(e)) from e
        except anthropic_sdk.APIConnectionError as e:
            raise LLMUnavailableError(str(e)) from e
        except anthropic_sdk.APIStatusError as e:
            raise LLMUnavailableError(f"{e.status_code}: {e.message}") from e
        except Exception as e:
            raise LLMProviderError(str(e)) from e
        result = LLMResponse(
            texto=resp.content[0].text,
            tokens_input=resp.usage.input_tokens,
            tokens_output=resp.usage.output_tokens,
        )
        if self._tracker is not None:
            self._tracker.record(
                UsageRecord(
                    momento=datetime.now(),
                    provider="anthropic",
                    modelo=self._modelo,
                    tokens_input=resp.usage.input_tokens,
                    tokens_output=resp.usage.output_tokens,
                    custo_usd=estimar_custo(
                        self._modelo, resp.usage.input_tokens, resp.usage.output_tokens
                    ),
                )
            )
        return result
