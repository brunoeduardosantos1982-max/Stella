"""Testes do AutoQA — checklist da marca + ciclo refazer/aceitar_com_aviso."""

from stella.agents.agente_marca_mktmagneto.autoqa import AutoQA
from stella.agents.agente_marca_mktmagneto.redator import PostTexto
from stella.framework.testing.fakes import FakeLLM


def _post_ok() -> PostTexto:
    return PostTexto(
        pilar=1,
        titulo="x",
        legenda="🔥 Hook bom\n\nctx\n\ncorpo com 'como real' aqui\n\n👇 Comenta X",
        hashtags=["#a"] * 12,
        slides=["s1", "s2", "s3"],
    )


def test_post_bom_aprovado():
    qa = AutoQA(llm=FakeLLM(responses=["veredicto: aprovado\nmotivo: ok"]))
    r = qa.revisar(_post_ok(), knowledge={"briefing": "..."}, tentativa=1)
    assert r.veredicto == "aprovado"


def test_post_ruim_pede_refazer_na_primeira():
    qa = AutoQA(llm=FakeLLM(responses=["veredicto: refazer\nmotivo: hook fraco"]))
    r = qa.revisar(_post_ok(), knowledge={"briefing": "..."}, tentativa=1)
    assert r.veredicto == "refazer"
    assert "hook fraco" in r.motivo


def test_post_ruim_aceita_com_aviso_na_segunda():
    qa = AutoQA(llm=FakeLLM(responses=["veredicto: refazer\nmotivo: hook fraco"]))
    r = qa.revisar(_post_ok(), knowledge={"briefing": "..."}, tentativa=2)
    assert r.veredicto == "aceito_com_aviso"
    assert "hook fraco" in r.aviso


def test_yaml_invalido_devolve_aprovado_com_aviso():
    """Robustez: LLM resposta não-YAML não trava o pipeline."""
    qa = AutoQA(llm=FakeLLM(responses=["garbage :::: not yaml"]))
    r = qa.revisar(_post_ok(), knowledge={"briefing": "..."}, tentativa=1)
    # Default fail-open: trata como aprovado para não bloquear, mas avisa
    assert r.veredicto == "aprovado"
    assert "yaml" in r.aviso.lower() or "parse" in r.aviso.lower()


def test_prompt_inclui_briefing_e_legenda():
    """O prompt deve incluir o briefing (gabarito) e a legenda (a ser revisada)."""
    llm = FakeLLM(responses=["veredicto: aprovado\nmotivo: ok"])
    qa = AutoQA(llm=llm)
    post = _post_ok()
    qa.revisar(post, knowledge={"briefing": "GABARITO_DA_MARCA"}, tentativa=1)
    p = llm.calls[0]
    assert "GABARITO_DA_MARCA" in p
    assert "Hook bom" in p
