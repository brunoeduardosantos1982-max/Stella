"""Unit tests do especialista copywriter."""

from typing import cast

from stella.adapters.llm.router import LLMRouter
from stella.agents.copywriter.agent import Agent as Copywriter
from stella.framework.testing.fakes import FakeLLM


class _FakeRouter:
    def __init__(self, llm: FakeLLM) -> None:
        self._llm = llm

    def select(self, complexity: str = "low") -> FakeLLM:
        return self._llm

    def with_minimum(self, modelo: object) -> "_FakeRouter":
        return self


_COPY_YAML = """
legenda: "🔥 Hook real\n\nContexto aqui\n\n👇 Comenta AGENTE"
slides:
  - "Slide 1 — ideia"
  - "Slide 2 — como"
  - "Slide 3 — resultado"
hashtags:
  - "#ia"
  - "#marketingdigital"
  - "#automacao"
  - "#ia2"
  - "#ia3"
  - "#ia4"
  - "#ia5"
  - "#ia6"
  - "#ia7"
  - "#ia8"
  - "#ia9"
  - "#ia10"
rationale: "Apliquei PAS: problema, agitação, solução"
"""

_KP = {
    "voz": "direto, sem hype",
    "cta_padrao": "Comenta AGENTE",
    "hashtags_base": ["#ia"],
}

_PAUTA = {"pilar": 1, "titulo": "99% conversa, 1% constrói", "tipo": "carrossel", "n_slides": 3}


def _agent(responses: list[str]) -> Copywriter:
    llm = FakeLLM(responses=responses)
    return Copywriter(llm=cast(LLMRouter, _FakeRouter(llm)))


def test_copywriter_retorna_legenda_slides_hashtags_rationale() -> None:
    agent = _agent([_COPY_YAML])
    out = agent.execute({"knowledge_pack": _KP, "pauta": _PAUTA})
    assert out.sucesso is True
    assert out.resultado["legenda"].startswith("🔥")
    assert len(out.resultado["slides"]) == 3
    assert len(out.resultado["hashtags"]) == 12
    assert out.resultado["rationale"] != ""


_COPY_ESTRUTURADO = """
legenda: "🔥 Hook\n\nx\n\n👇 CTA"
headline_hero: "20 MITOS DA IA"
slides:
  - titulo: "O mito"
    corpo: "todo mundo acha que IA é chat"
    destaque: "chat"
  - titulo: "A virada"
    corpo: "IA é sistema que roda sozinho"
    terminal: "$ comenta AGENTE"
    label: "salva esse post"
hashtags: ["#ia"]
rationale: "PAS"
"""


def test_copywriter_slides_estruturados_e_headline_hero() -> None:
    out = _agent([_COPY_ESTRUTURADO]).execute({"knowledge_pack": _KP, "pauta": _PAUTA})
    assert out.resultado["headline_hero"] == "20 MITOS DA IA"
    s0, s1 = out.resultado["slides"]
    assert s0 == {
        "titulo": "O mito",
        "corpo": "todo mundo acha que IA é chat",
        "destaque": "chat",
        "terminal": "",
        "label": "",
    }
    assert s1["terminal"] == "$ comenta AGENTE"
    assert s1["label"] == "salva esse post"


def test_copywriter_slide_string_legado_vira_corpo() -> None:
    out = _agent([_COPY_YAML]).execute({"knowledge_pack": _KP, "pauta": _PAUTA})
    s = out.resultado["slides"][0]
    assert s["corpo"] == "Slide 1 — ideia"
    assert s["titulo"] == ""


def test_copywriter_sem_knowledge_pack_retorna_sucesso_false() -> None:
    agent = _agent([])
    out = agent.execute({"pauta": _PAUTA})
    assert out.sucesso is False
    assert any("knowledge_pack" in m for m in out.mensagens)


def test_copywriter_sem_pauta_retorna_sucesso_false() -> None:
    agent = _agent([])
    out = agent.execute({"knowledge_pack": _KP})
    assert out.sucesso is False
    assert any("pauta" in m for m in out.mensagens)


def test_copywriter_sem_llm_retorna_sucesso_false() -> None:
    agent = Copywriter()
    out = agent.execute({"knowledge_pack": _KP, "pauta": _PAUTA})
    assert out.sucesso is False


def test_copywriter_incorpora_feedback_anterior_no_prompt() -> None:
    """Quando feedback_anterior está no payload, aparece no prompt enviado ao LLM."""
    llm = FakeLLM(responses=[_COPY_YAML])
    agent = Copywriter(llm=cast(LLMRouter, _FakeRouter(llm)))
    agent.execute(
        {
            "knowledge_pack": _KP,
            "pauta": _PAUTA,
            "feedback_anterior": "legenda muito longa, encurtar",
            "output_anterior": {"legenda": "legenda antiga"},
        }
    )
    assert "legenda muito longa" in llm.calls[0]


def test_copywriter_yaml_malformado_retorna_resultado_vazio_mas_nao_crasha() -> None:
    agent = _agent(["isto nao é YAML válido {{{"])
    out = agent.execute({"knowledge_pack": _KP, "pauta": _PAUTA})
    assert out.sucesso is False
    assert isinstance(out.resultado, dict)


def test_copywriter_descoberto_pelo_agent_registry() -> None:
    """manifest.yaml é válido e o AgentRegistry descobre o copywriter."""
    from pathlib import Path

    from stella.framework.registry import AgentRegistry

    reg = AgentRegistry(Path("stella/agents"))
    assert "copywriter" in reg.list_nomes()
    copywriter_m = next(x for x in reg.list_manifests() if x.nome == "copywriter")
    assert copywriter_m.setor == "marketing"
    assert copywriter_m.tipo == "especialista"
