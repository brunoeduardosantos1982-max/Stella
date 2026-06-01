from typing import cast

from stella.adapters.llm.router import LLMRouter
from stella.agents.copywriter.agent import Agent
from stella.framework.testing.fakes import FakeLLM


class _Router:
    def __init__(self, llm: FakeLLM) -> None:
        self._llm = llm

    def select(self, complexity: str = "low") -> FakeLLM:
        return self._llm


def test_prompt_usa_briefing_e_referencia() -> None:
    llm = FakeLLM(responses=["legenda: ok\nslides: []\nhashtags: []\nrationale: r\n"])
    ag = Agent(llm=cast(LLMRouter, _Router(llm)))
    out = ag.execute(
        {
            "knowledge_pack": {"briefing": "B", "referencia": "REF-XYZ-789"},
            "pauta": {"pilar": 1, "titulo": "5 mitos", "tipo": "carrossel", "n_slides": 3},
            "briefing": {
                "angulo": "ang",
                "gancho_padrao_id": "mito-verdade",
                "gancho_instrucao": "abra com o mito",
                "pontos_chave": ["Claude Code", "Apify"],
                "cta_unico": "Comenta MITO",
                "hashtags_sugeridas": ["#IA"],
            },
        }
    )
    assert out.sucesso
    p = llm.calls[0]
    assert "REF-XYZ-789" in p
    assert "Claude Code" in p
    assert "Comenta MITO" in p
    assert "mito" in p.lower()
