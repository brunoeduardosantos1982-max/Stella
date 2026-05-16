from anthropic import Anthropic

from stella.adapters.llm.base import LLMProvider, LLMResponse, Message

_MODELO = "claude-sonnet-4-6"
_MAX_TOKENS = 4096


class AnthropicProvider(LLMProvider):
    """Provedor LLM usando Claude Sonnet 4.6 via Anthropic.

    O parâmetro `client` permite injetar um dublê nos testes.
    A API Anthropic trata `system` como parâmetro separado, não como mensagem.
    """

    def __init__(self, api_key: str, client=None):
        self._client = client or Anthropic(api_key=api_key)

    def complete(self, prompt: str) -> LLMResponse:
        return self.chat([Message(role="user", content=prompt)])

    def chat(self, messages: list[Message]) -> LLMResponse:
        system_parts = [m.content for m in messages if m.role == "system"]
        conversa = [
            {"role": m.role, "content": m.content}
            for m in messages
            if m.role != "system"
        ]
        kwargs = {
            "model": _MODELO,
            "max_tokens": _MAX_TOKENS,
            "messages": conversa,
        }
        if system_parts:
            kwargs["system"] = "\n\n".join(system_parts)

        resp = self._client.messages.create(**kwargs)
        return LLMResponse(
            texto=resp.content[0].text,
            tokens_input=resp.usage.input_tokens,
            tokens_output=resp.usage.output_tokens,
        )
