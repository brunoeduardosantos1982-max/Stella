from stella.agents.designer.agent import Agent
from stella.framework.testing.fakes import FakeLLM


class _Router:
    def __init__(self, llm: FakeLLM) -> None:
        self._llm = llm

    def select(self, complexity: str = "low") -> FakeLLM:
        return self._llm


def test_designer_escolhe_foto_hero_com_tema() -> None:
    yaml_resp = (
        "rota: foto-hero\ntema: mitos\ntemplate_escolhido: capa-carrossel\n"
        "foto_escolhida: \nsoul_id_prompt: null\nreferencias_usadas: []\nrationale: ok\n"
        "foto_hero:\n  headline: '5 MITOS\\nSOBRE IA'\n  label_topo: 'PARE'\n"
        "  sublabel: 'a verdade'\n  anotacoes: ['a ->','<- b']\n  logos: ['claude','openai']\n"
    )
    ag = Agent.__new__(Agent)
    ag._llm = _Router(FakeLLM(responses=[yaml_resp]))  # type: ignore[attr-defined]

    d = ag._decidir_template(
        knowledge_pack={},
        pauta={"tipo": "carrossel", "titulo": "t"},
        copy={"legenda": "x"},
        fotos=[],
    )

    assert d["rota"] == "foto-hero"
    assert d["tema"] == "mitos"
    assert d["foto_hero"]["headline"].startswith("5 MITOS")
