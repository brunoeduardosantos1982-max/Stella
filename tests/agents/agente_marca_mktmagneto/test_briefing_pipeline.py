from dataclasses import asdict

from stella.agents.copywriter.briefing import MontadorBriefing
from stella.agents.copywriter.ganchos import GanchoCatalog
from stella.framework.testing.fakes import FakeLLM


def test_briefing_montado_vira_dict(tmp_path) -> None:
    p = tmp_path / "s.json"
    p.write_text('{"padroes":[]}', encoding="utf-8")
    m = MontadorBriefing(
        llm=FakeLLM(responses=["angulo: a\ngancho_padrao_id: x\ncta_unico: C\n"]),
        ganchos=GanchoCatalog(path=str(p)),
    )
    b = m.montar(pauta={"titulo": "T", "pilar": 1}, knowledge_pauta={"referencia": "R"})
    payload = {
        "knowledge_pack": {"referencia": "R"},
        "pauta": {"titulo": "T"},
        "briefing": asdict(b),
    }
    assert payload["briefing"]["cta_unico"] == "C"
