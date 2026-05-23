"""Pipeline de texto end-to-end (sem visual/fila) — Task 13."""

from typing import Any, cast

from stella.adapters.llm.base import LLMProvider
from stella.adapters.llm.router import LLMRouter
from stella.agents.agente_marca_mktmagneto.agent import Agent
from stella.agents.agente_marca_mktmagneto.redator import PostTexto
from stella.framework.testing.fakes import FakeLLM, FakeMCP, FakeVault

_BASE = "C04 Claude Obsidian/projetos e specs/mktmagneto.ia/"


def _vault_com_docs() -> FakeVault:
    return FakeVault(
        {
            f"{_BASE}mktmagneto.ia — 01 Spec.md": ("# Spec\n\nposicionamento", {}),
            f"{_BASE}mktmagneto.ia — 03 Briefing do Agente de Conteúdo.md": (
                "# Briefing\n\nvoz direta",
                {},
            ),
            f"{_BASE}mktmagneto.ia — 04 Kit de Identidade Visual.md": ("# Kit\n\ncores", {}),
        }
    )


_PLAN_YAML = """
pautas:
  - {pilar: 1, titulo: "A"}
  - {pilar: 2, titulo: "B"}
  - {pilar: 4, titulo: "C"}
"""

_REDATOR_YAML = """
legenda: "🔥 H\\n\\nctx\\n\\ncorpo\\n\\n👇 CTA"
hashtags: ["#h1", "#h2", "#h3", "#h4", "#h5", "#h6", "#h7", "#h8", "#h9", "#h10", "#h11", "#h12"]
slides: ["s1", "s2", "s3"]
"""


class _FakeRouter:
    """Stub mínimo de LLMRouter — devolve sempre o mesmo FakeLLM."""

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    def select(self, complexity: str) -> LLMProvider:
        return self._llm


def test_pipeline_de_texto_gera_3_posts() -> None:
    """Pipeline texto: 4 módulos encadeados → 3 PostTexto no resultado."""
    vault = _vault_com_docs()
    # 1 chamada do Planejador + 3 chamadas do Redator = 4 respostas
    llm = FakeLLM(responses=[_PLAN_YAML, _REDATOR_YAML, _REDATOR_YAML, _REDATOR_YAML])
    brave: Any = FakeMCP(
        nome="brave-search",
        category="research",
        resultados={
            "pilar 1 tendências 2026": [{"titulo": "x"}],
            "pilar 2 tendências 2026": [{"titulo": "y"}],
            "pilar 3 tendências 2026": [{"titulo": "z"}],
            "pilar 4 tendências 2026": [{"titulo": "w"}],
        },
    )

    agent = Agent(vault=vault, llm=cast(LLMRouter, _FakeRouter(llm)), mcps=[brave])
    out = agent.execute({})

    assert out.sucesso is True
    posts = out.resultado["posts_textos"]
    assert len(posts) == 3
    assert all(isinstance(p, PostTexto) for p in posts)
    assert {p.pilar for p in posts} == {1, 2, 4}


def test_doc_da_marca_ausente_devolve_sucesso_false() -> None:
    """Sem briefing no vault, agente não roda."""
    vault_vazio = FakeVault({})
    llm = FakeLLM(responses=[])
    agent = Agent(vault=vault_vazio, llm=cast(LLMRouter, _FakeRouter(llm)), mcps=[])
    out = agent.execute({})
    assert out.sucesso is False
    assert any(
        "marca" in m.lower() or "spec" in m.lower() or "briefing" in m.lower()
        for m in out.mensagens
    )


def test_sem_vault_ou_llm_falha_graciosamente() -> None:
    """Sem deps essenciais injetadas, agente devolve sucesso=False."""
    agent = Agent()  # nada injetado
    out = agent.execute({})
    assert out.sucesso is False
