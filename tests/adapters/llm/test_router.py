import pytest

from stella.adapters.llm.base import LLMProvider, LLMResponse, Message
from stella.adapters.llm.router import LLMRouter
from stella.domain.enums import ModeloIA


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


def test_with_minimum_sonnet_escala_pedido_de_gemma(gemma, anthropic):
    """Se manifest exige Sonnet, with_minimum forca Anthropic mesmo em complexity='low'."""
    router = LLMRouter(gemma=gemma, anthropic=anthropic, default="gemma")
    proxy = router.with_minimum(ModeloIA.SONNET)
    assert proxy.select(complexity="low").nome == "anthropic"


def test_with_minimum_opus_fallback_para_anthropic_sem_opus(gemma, anthropic):
    """Compat FB-M3: sem slot opus configurado, with_minimum(OPUS) escala para Sonnet."""
    router = LLMRouter(gemma=gemma, anthropic=anthropic, default="gemma")
    proxy = router.with_minimum(ModeloIA.OPUS)
    assert proxy.select(complexity="low").nome == "anthropic"


def test_with_minimum_opus_usa_opus_provider_quando_existe(gemma, anthropic):
    """FB-M4: quando slot opus configurado, with_minimum(OPUS) usa opus real."""
    opus = _ProviderDummy("opus")
    router = LLMRouter(gemma=gemma, anthropic=anthropic, opus=opus, default="gemma")
    proxy = router.with_minimum(ModeloIA.OPUS)
    assert proxy.select(complexity="low").nome == "opus"


def test_with_minimum_sonnet_ainda_usa_anthropic_mesmo_com_opus(gemma, anthropic):
    """Slot opus nao interfere quando minimo=SONNET (apenas para OPUS)."""
    opus = _ProviderDummy("opus")
    router = LLMRouter(gemma=gemma, anthropic=anthropic, opus=opus, default="gemma")
    proxy = router.with_minimum(ModeloIA.SONNET)
    assert proxy.select(complexity="low").nome == "anthropic"


def test_with_minimum_gemma_nao_altera_comportamento(gemma, anthropic):
    """Minimo GEMMA = router devolve o que escolheria normalmente."""
    router = LLMRouter(gemma=gemma, anthropic=anthropic, default="gemma")
    proxy = router.with_minimum(ModeloIA.GEMMA)
    assert proxy.select(complexity="low").nome == "gemma"


def test_with_minimum_preserva_force_minimo_ganha_de_force_baixo(gemma, anthropic):
    """force='gemma' + minimo=sonnet -> sonnet (minimo manda)."""
    router = LLMRouter(gemma=gemma, anthropic=anthropic, default="gemma")
    proxy = router.with_minimum(ModeloIA.SONNET)
    assert proxy.select(force="gemma").nome == "anthropic"


def test_with_minimum_complexity_high_ainda_usa_anthropic(gemma, anthropic):
    """Complexity high + minimo gemma: comportamento normal, escala normalmente."""
    router = LLMRouter(gemma=gemma, anthropic=anthropic, default="gemma")
    proxy = router.with_minimum(ModeloIA.GEMMA)
    assert proxy.select(complexity="high").nome == "anthropic"
