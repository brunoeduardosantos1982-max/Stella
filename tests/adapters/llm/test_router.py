import pytest

from stella.adapters.llm.base import LLMProvider, LLMResponse, Message
from stella.adapters.llm.router import LLMRouter


class _ProviderDummy(LLMProvider):
    def __init__(self, nome):
        self.nome = nome

    def complete(self, prompt: str) -> LLMResponse:
        return LLMResponse(texto=self.nome)

    def chat(self, messages: list[Message]) -> LLMResponse:
        return LLMResponse(texto=self.nome)


@pytest.fixture
def gemma():
    return _ProviderDummy("gemma")


@pytest.fixture
def anthropic():
    return _ProviderDummy("anthropic")


def test_default_gemma_escolhe_gemma_para_baixa_complexidade(gemma, anthropic):
    router = LLMRouter(gemma=gemma, anthropic=anthropic, default="gemma")
    assert router.select(complexity="low").nome == "gemma"


def test_alta_complexidade_escolhe_anthropic(gemma, anthropic):
    router = LLMRouter(gemma=gemma, anthropic=anthropic, default="gemma")
    assert router.select(complexity="high").nome == "anthropic"


def test_force_sonnet_ignora_complexidade(gemma, anthropic):
    router = LLMRouter(gemma=gemma, anthropic=anthropic, default="gemma")
    assert router.select(complexity="low", force="sonnet").nome == "anthropic"


def test_force_gemma_ignora_complexidade(gemma, anthropic):
    router = LLMRouter(gemma=gemma, anthropic=anthropic, default="gemma")
    assert router.select(complexity="high", force="gemma").nome == "gemma"


def test_default_sonnet_escolhe_anthropic_para_baixa_complexidade(gemma, anthropic):
    router = LLMRouter(gemma=gemma, anthropic=anthropic, default="sonnet")
    assert router.select(complexity="low").nome == "anthropic"


def test_usa_skill_forca_anthropic(gemma, anthropic):
    router = LLMRouter(gemma=gemma, anthropic=anthropic, default="gemma")
    assert router.select(complexity="low", usa_skill_ou_mcp=True).nome == "anthropic"
