from datetime import datetime
from typing import Any

from anthropic import Anthropic

from stella.adapters.llm.base import LLMProvider, LLMResponse, Message
from stella.infra.usage_tracker import UsageRecord, UsageTracker, estimar_custo

_MODELO = "claude-sonnet-4-6"
_MAX_TOKENS = 4096


class AnthropicProvider(LLMProvider):
    """Provedor LLM usando Claude Sonnet 4.6 via Anthropic.

    O parâmetro `client` permite injetar um dublê nos testes.
    A API Anthropic trata `system` como parâmetro separado, não como mensagem.
    """

    def __init__(
        self,
        api_key: str,
        client: Any = None,
        tracker: UsageTracker | None = None,
    ) -> None:
        self._client = client or Anthropic(api_key=api_key)
        self._tracker = tracker

    def complete(self, prompt: str) -> LLMResponse:
        return self.chat([Message(role="user", content=prompt)])

    def chat(self, messages: list[Message]) -> LLMResponse:
        system_parts = [m.content for m in messages if m.role == "system"]
        conversa = [{"role": m.role, "content": m.content} for m in messages if m.role != "system"]
        kwargs = {
            "model": _MODELO,
            "max_tokens": _MAX_TOKENS,
            "messages": conversa,
        }
        if system_parts:
            kwargs["system"] = "\n\n".join(system_parts)

        resp = self._client.messages.create(**kwargs)
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
                    modelo=_MODELO,
                    tokens_input=resp.usage.input_tokens,
                    tokens_output=resp.usage.output_tokens,
                    custo_usd=estimar_custo(
                        _MODELO, resp.usage.input_tokens, resp.usage.output_tokens
                    ),
                )
            )
        return result
