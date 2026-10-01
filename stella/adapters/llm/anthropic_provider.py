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

_MODELO_DEFAULT = "claude-sonnet-5-5"
# No Sonnet 5.5 o raciocínio fica sempre ligado e conta dentro do max_tokens,
# mesmo quando o texto dele não volta: 4096 truncava a resposta.
_MAX_TOKENS_DEFAULT = 16000
# Ponto de partida do guia para geração de conteúdo, extração e classificação,
# que é todo o trabalho da fábrica. Mais esforço = mais raciocínio e custo.
_ESFORCO_DEFAULT = "low"


class AnthropicProvider(LLMProvider):
    """Provedor LLM usando modelos Claude via Anthropic.

    O parâmetro `client` permite injetar um dublê nos testes.
    A API Anthropic trata `system` como parâmetro separado, não como mensagem.

    FB-M4: parametro `modelo` permite usar Sonnet, Opus ou qualquer outro
    modelo Claude. Default: Sonnet 5.5, com esforço `low`.
    """

    def __init__(
        self,
        api_key: str,
        client: Any = None,
        max_tokens: int = _MAX_TOKENS_DEFAULT,
        tracker: UsageTracker | None = None,
        modelo: str = _MODELO_DEFAULT,
        esforco: str = _ESFORCO_DEFAULT,
    ) -> None:
        self._client: Any = client or Anthropic(api_key=api_key)
        self._max_tokens = max_tokens
        self._tracker = tracker
        self._modelo = modelo
        self._esforco = esforco

    def complete(self, prompt: str, schema: dict[str, Any] | None = None) -> LLMResponse:
        return self.chat([Message(role="user", content=prompt)], schema=schema)

    def chat(self, messages: list[Message], schema: dict[str, Any] | None = None) -> LLMResponse:
        system_parts = [m.content for m in messages if m.role == "system"]
        conversa = [{"role": m.role, "content": m.content} for m in messages if m.role != "system"]
        output_config: dict[str, Any] = {"effort": self._esforco}
        if schema is not None:
            # Saída estruturada: a API garante JSON válido no formato do schema.
            output_config["format"] = {"type": "json_schema", "schema": schema}
        kwargs: dict[str, Any] = {
            "model": self._modelo,
            "max_tokens": self._max_tokens,
            "messages": conversa,
            "output_config": output_config,
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
        motivo = getattr(resp, "stop_reason", None)
        if motivo == "refusal":
            detalhe = getattr(resp, "stop_details", None)
            categoria = getattr(detalhe, "category", None) if detalhe else None
            raise LLMProviderError(f"o modelo recusou o pedido (categoria: {categoria})")
        if motivo == "max_tokens":
            # Resposta cortada no meio: JSON quebrado ou texto pela metade.
            raise LLMProviderError(f"resposta cortada no limite de {self._max_tokens} tokens")
        # Lê pelo tipo do bloco: com raciocínio ligado a resposta pode começar
        # com um bloco `thinking` (vazio por padrão) antes do texto.
        texto = "".join(b.text for b in resp.content if getattr(b, "type", "text") == "text")
        result = LLMResponse(
            texto=texto,
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
