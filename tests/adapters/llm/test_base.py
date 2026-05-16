import pytest

from stella.adapters.llm.base import LLMProvider, LLMResponse, Message


def test_message_estrutura():
    m = Message(role="user", content="olá")
    assert m.role == "user"
    assert m.content == "olá"


def test_llm_response_estrutura():
    r = LLMResponse(texto="resposta", tokens_input=10, tokens_output=5)
    assert r.texto == "resposta"
    assert r.tokens_input == 10
    assert r.tokens_output == 5


def test_llm_provider_e_abstrato():
    with pytest.raises(TypeError):
        LLMProvider()  # type: ignore[abstract]
