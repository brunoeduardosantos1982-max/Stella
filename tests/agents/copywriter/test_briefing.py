from stella.agents.copywriter.briefing import BriefingCopy, MontadorBriefing
from stella.agents.copywriter.ganchos import GanchoCatalog
from stella.framework.testing.fakes import FakeLLM


def _ganchos(tmp_path) -> GanchoCatalog:
    p = tmp_path / "swipe.json"
    p.write_text(
        '{"padroes":[{"id":"mito-verdade","nome":"Mito","estrutura":"a","quando_usar":"q"}]}',
        encoding="utf-8",
    )
    return GanchoCatalog(path=str(p))


def test_montar_devolve_briefing(tmp_path) -> None:
    yaml_resp = (
        "angulo: desmistificar IA\n"
        "gancho_padrao_id: mito-verdade\n"
        "gancho_instrucao: abra com o mito mais perigoso\n"
        "pontos_chave: ['Claude Code', 'Apify', 'Manis']\n"
        "cta_unico: Comenta MITO\n"
        "hashtags_sugeridas: ['#IA','#mktmagnetoia']\n"
    )
    m = MontadorBriefing(llm=FakeLLM(responses=[yaml_resp]), ganchos=_ganchos(tmp_path))
    b = m.montar(
        pauta={"titulo": "5 mitos", "pilar": 1},
        knowledge_pauta={"briefing": "B", "referencia": "lista: Claude Code, Apify, Manis"},
    )
    assert isinstance(b, BriefingCopy)
    assert b.gancho_padrao_id == "mito-verdade"
    assert "Claude Code" in b.pontos_chave
    assert b.cta_unico == "Comenta MITO"


def test_yaml_invalido_briefing_minimo(tmp_path) -> None:
    m = MontadorBriefing(llm=FakeLLM(responses=["lixo ::: nao yaml"]), ganchos=_ganchos(tmp_path))
    b = m.montar(pauta={"titulo": "T", "pilar": 1}, knowledge_pauta={})
    assert isinstance(b, BriefingCopy)
    assert b.angulo
    assert b.pontos_chave == []


def test_prompt_inclui_referencia_e_padroes(tmp_path) -> None:
    llm = FakeLLM(responses=["angulo: x\ngancho_padrao_id: mito-verdade\n"])
    m = MontadorBriefing(llm=llm, ganchos=_ganchos(tmp_path))
    m.montar(pauta={"titulo": "T", "pilar": 1}, knowledge_pauta={"referencia": "REF-CONCRETA-123"})
    assert "REF-CONCRETA-123" in llm.calls[0]
    assert "mito-verdade" in llm.calls[0]
