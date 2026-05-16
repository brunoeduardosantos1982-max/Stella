from dataclasses import dataclass

from stella.adapters.llm.anthropic_provider import AnthropicProvider
from stella.adapters.llm.base import Message


# --- Dublês do SDK Anthropic ---
@dataclass
class _FakeUsage:
    input_tokens: int
    output_tokens: int


@dataclass
class _FakeTextBlock:
    text: str


@dataclass
class _FakeAnthropicResponse:
    content: list
    usage: _FakeUsage


class _FakeMessages:
    def __init__(self, resposta_texto):
        self._resposta_texto = resposta_texto
        self.ultima_chamada = None

    def create(self, **kwargs):
        self.ultima_chamada = kwargs
        return _FakeAnthropicResponse(
            content=[_FakeTextBlock(text=self._resposta_texto)],
            usage=_FakeUsage(input_tokens=20, output_tokens=9),
        )


class _FakeAnthropicClient:
    def __init__(self, resposta_texto="resposta do sonnet"):
        self.messages = _FakeMessages(resposta_texto)


# --- Testes ---
def test_complete_retorna_llm_response():
    fake = _FakeAnthropicClient("olá do sonnet")
    provider = AnthropicProvider(api_key="ant-teste", client=fake)
    resp = provider.complete("diga olá")
    assert resp.texto == "olá do sonnet"
    assert resp.tokens_input == 20
    assert resp.tokens_output == 9


def test_complete_usa_modelo_sonnet():
    fake = _FakeAnthropicClient()
    provider = AnthropicProvider(api_key="ant-teste", client=fake)
    provider.complete("oi")
    assert fake.messages.ultima_chamada["model"] == "claude-sonnet-4-6"


def test_chat_separa_system_das_demais_mensagens():
    fake = _FakeAnthropicClient("resposta")
    provider = AnthropicProvider(api_key="ant-teste", client=fake)
    provider.chat(
        [
            Message(role="system", content="você é a Stella"),
            Message(role="user", content="oi"),
        ]
    )
    chamada = fake.messages.ultima_chamada
    assert chamada["system"] == "você é a Stella"
    assert chamada["messages"] == [{"role": "user", "content": "oi"}]
