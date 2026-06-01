from stella.agents.agente_marca_mktmagneto.diretor import (
    AtribuicaoEditorial,
    DiretorCriativo,
)
from stella.agents.agente_marca_mktmagneto.planejador import Pauta
from stella.framework.testing.fakes import FakeLLM

TEMAS = ["mitos", "tech", "segredos"]


def _pautas() -> list[Pauta]:
    return [
        Pauta(pilar=1, titulo="5 mitos"),
        Pauta(pilar=2, titulo="5 ferramentas"),
        Pauta(pilar=2, titulo="como montar agente"),
    ]


def test_atribui_e_parseia() -> None:
    yaml_resp = (
        "atribuicoes:\n"
        "  - rota: foto-hero\n    tema: mitos\n    gancho_padrao_id: mito-verdade\n"
        "  - rota: foto-hero\n    tema: tech\n    gancho_padrao_id: testei-descobri\n"
        "  - rota: tipografico\n    tema: \n    gancho_padrao_id: passo-a-passo\n"
    )
    d = DiretorCriativo(llm=FakeLLM(responses=[yaml_resp]), temas_disponiveis=TEMAS)
    out = d.dirigir(pautas=_pautas(), knowledge={"briefing": "B"}, digest="D")
    assert isinstance(out[0], AtribuicaoEditorial)
    assert len(out) == 3
    assert out[0].tema == "mitos" and out[0].rota == "foto-hero"
    assert out[2].rota == "tipografico"


def test_variedade_forcada_quando_llm_repete() -> None:
    yaml_resp = (
        "atribuicoes:\n"
        "  - rota: tipografico\n    tema: \n    gancho_padrao_id: a\n"
        "  - rota: tipografico\n    tema: \n    gancho_padrao_id: b\n"
        "  - rota: tipografico\n    tema: \n    gancho_padrao_id: c\n"
    )
    out = DiretorCriativo(llm=FakeLLM(responses=[yaml_resp]), temas_disponiveis=TEMAS).dirigir(
        pautas=_pautas(), knowledge={}, digest=""
    )
    rotas = {a.rota for a in out}
    assert len(rotas) >= 2
    assert any(a.rota == "foto-hero" for a in out)


def test_tema_invalido_vira_tipografico() -> None:
    yaml_resp = (
        "atribuicoes:\n  - rota: foto-hero\n    tema: inexistente\n    gancho_padrao_id: x\n"
        "  - rota: tipografico\n    tema: \n    gancho_padrao_id: y\n"
        "  - rota: foto-local\n    tema: \n    gancho_padrao_id: z\n"
    )
    out = DiretorCriativo(llm=FakeLLM(responses=[yaml_resp]), temas_disponiveis=TEMAS).dirigir(
        pautas=_pautas(), knowledge={}, digest=""
    )
    assert out[0].rota == "tipografico" and out[0].tema is None


def test_llm_invalido_default_resiliente() -> None:
    out = DiretorCriativo(
        llm=FakeLLM(responses=["lixo ::: nao yaml"]), temas_disponiveis=TEMAS
    ).dirigir(pautas=_pautas(), knowledge={}, digest="")
    assert len(out) == 3
    assert any(a.rota == "foto-hero" for a in out)
