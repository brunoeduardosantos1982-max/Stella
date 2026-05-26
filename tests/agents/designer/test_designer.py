"""Unit tests do especialista designer."""

from typing import cast

import pytest

from stella.adapters.llm.router import LLMRouter
from stella.agents.designer.agent import Agent as Designer
from stella.framework.testing.fakes import FakeLLM, FakeVault

_T7_MSG = "T5 refatorou para DesignSpecGenerator (sem PNG); T7/T8 atualizam estes testes"


class _FakeRouter:
    def __init__(self, llm: FakeLLM) -> None:
        self._llm = llm

    def select(self, complexity: str = "low") -> FakeLLM:
        return self._llm

    def with_minimum(self, modelo: object) -> "_FakeRouter":
        return self


_TEMPLATE_PATH = "C04 Claude Obsidian/outputs/mktmagneto-ia/templates/capa-carrossel.html"
_TEMPLATE_HTML = "<html><body>{{TITULO}} {{SLIDE_1}}</body></html>"

_DESIGN_YAML = """
template_escolhido: capa-carrossel
rationale: "Escolhido pela densidade informacional do carrossel"
"""

_COPY = {
    "legenda": "🔥 Hook\n\nContexto\n\n👇 CTA",
    "slides": ["Slide 1 — intro", "Slide 2 — meio", "Slide 3 — fim"],
    "hashtags": ["#ia"] * 12,
    "rationale": "copy rationale",
}

_KP = {
    "voz": "direto, sem hype",
    "paleta": {"primaria": "#00FFFF", "secundaria": "#556B2F"},
}

_PAUTA = {"pilar": 1, "titulo": "Título do post", "tipo": "carrossel", "n_slides": 3}


def _vault_com_template() -> FakeVault:
    return FakeVault({_TEMPLATE_PATH: (_TEMPLATE_HTML, {})})


def _agent(responses: list[str], vault: FakeVault | None = None) -> Designer:
    llm = FakeLLM(responses=responses)
    return Designer(
        llm=cast(LLMRouter, _FakeRouter(llm)),
        vault=vault or _vault_com_template(),
    )


@pytest.mark.xfail(reason=_T7_MSG, strict=True)
def test_designer_retorna_png_bytes_template_rationale() -> None:
    agent = _agent([_DESIGN_YAML])
    out = agent.execute({"knowledge_pack": _KP, "pauta": _PAUTA, "copy": _COPY})
    assert out.sucesso is True
    assert isinstance(out.resultado["png_bytes"], bytes)
    assert len(out.resultado["png_bytes"]) > 0
    assert out.resultado["template_escolhido"] == "capa-carrossel"
    assert out.resultado["rationale"] != ""
    assert out.resultado["slides_renderizados"] == 3


@pytest.mark.xfail(reason=_T7_MSG, strict=True)
def test_designer_sem_copy_retorna_sucesso_false() -> None:
    agent = _agent([])
    out = agent.execute({"knowledge_pack": _KP, "pauta": _PAUTA})
    assert out.sucesso is False
    assert any("copy" in m for m in out.mensagens)


@pytest.mark.xfail(reason=_T7_MSG, strict=True)
def test_designer_sem_knowledge_pack_retorna_sucesso_false() -> None:
    agent = _agent([])
    out = agent.execute({"copy": _COPY, "pauta": _PAUTA})
    assert out.sucesso is False
    assert any("knowledge_pack" in m for m in out.mensagens)


@pytest.mark.xfail(reason=_T7_MSG, strict=True)
def test_designer_sem_pauta_retorna_sucesso_false() -> None:
    agent = _agent([])
    out = agent.execute({"knowledge_pack": _KP, "copy": _COPY})
    assert out.sucesso is False
    assert any("pauta" in m for m in out.mensagens)


def test_designer_sem_llm_retorna_sucesso_false() -> None:
    agent = Designer(vault=_vault_com_template())
    out = agent.execute({"knowledge_pack": _KP, "pauta": _PAUTA, "copy": _COPY})
    assert out.sucesso is False


def test_designer_sem_vault_retorna_sucesso_false() -> None:
    agent = Designer()
    out = agent.execute({"knowledge_pack": _KP, "pauta": _PAUTA, "copy": _COPY})
    assert out.sucesso is False


@pytest.mark.xfail(reason=_T7_MSG, strict=True)
def test_designer_yaml_malformado_usa_template_default() -> None:
    agent = _agent(["isto nao é YAML {{{"])
    out = agent.execute({"knowledge_pack": _KP, "pauta": _PAUTA, "copy": _COPY})
    assert out.sucesso is True
    assert isinstance(out.resultado["png_bytes"], bytes)


def test_designer_descoberto_pelo_agent_registry() -> None:
    """manifest.yaml é válido e o AgentRegistry descobre o designer."""
    from pathlib import Path

    from stella.framework.registry import AgentRegistry

    reg = AgentRegistry(Path("stella/agents"))
    assert "designer" in reg.list_nomes()
    designer_m = next(x for x in reg.list_manifests() if x.nome == "designer")
    assert designer_m.setor == "marketing"
    assert designer_m.tipo == "especialista"
