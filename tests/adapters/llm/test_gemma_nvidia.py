from dataclasses import dataclass

from stella.adapters.llm.base import Message
from stella.adapters.llm.gemma_nvidia import GemmaNvidiaProvider


# --- Dublês do SDK OpenAI ---
@dataclass
class _FakeUsage:
    prompt_tokens: int
    completion_tokens: int


@dataclass
class _FakeMessage:
    content: str


@dataclass
class _FakeChoice:
    message: _FakeMessage


@dataclass
class _FakeCompletion:
    choices: list
    usage: _FakeUsage


class _FakeCompletions:
    def __init__(self, resposta_texto):
        self._resposta_texto = resposta_texto
        self.ultima_chamada = None

    def create(self, **kwargs):
        self.ultima_chamada = kwargs
        return _FakeCompletion(
            choices=[_FakeChoice(message=_FakeMessage(content=self._resposta_texto))],
            usage=_FakeUsage(prompt_tokens=12, completion_tokens=7),
        )


class _FakeChat:
    def __init__(self, resposta_texto):
        self.completions = _FakeCompletions(resposta_texto)


class _FakeOpenAIClient:
    def __init__(self, resposta_texto="resposta do gemma"):
        self.chat = _FakeChat(resposta_texto)


# --- Testes ---
def test_complete_retorna_llm_response():
    fake = _FakeOpenAIClient("olá do gemma")
    provider = GemmaNvidiaProvider(api_key="nv-teste", client=fake)
    resp = provider.complete("diga olá")
    assert resp.texto == "olá do gemma"
    assert resp.tokens_input == 12
    assert resp.tokens_output == 7


def test_complete_usa_modelo_gemma():
    fake = _FakeOpenAIClient()
    provider = GemmaNvidiaProvider(api_key="nv-teste", client=fake)
    provider.complete("oi")
    assert fake.chat.completions.ultima_chamada["model"] == "google/gemma-4-31b-it"


def test_chat_envia_mensagens_no_formato_correto():
    fake = _FakeOpenAIClient("resposta")
    provider = GemmaNvidiaProvider(api_key="nv-teste", client=fake)
    provider.chat(
        [
            Message(role="system", content="você é a Stella"),
            Message(role="user", content="oi"),
        ]
    )
    enviado = fake.chat.completions.ultima_chamada["messages"]
    assert enviado == [
        {"role": "system", "content": "você é a Stella"},
        {"role": "user", "content": "oi"},
    ]
