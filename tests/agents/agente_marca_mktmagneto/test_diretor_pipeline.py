from stella.agents.agente_marca_mktmagneto.diretor import DiretorCriativo
from stella.agents.agente_marca_mktmagneto.planejador import Pauta
from stella.framework.testing.fakes import FakeLLM


def test_diretor_produz_uma_atribuicao_por_pauta() -> None:
    pautas = [Pauta(1, "a"), Pauta(2, "b"), Pauta(2, "c")]
    yaml_resp = (
        "atribuicoes:\n  - rota: foto-hero\n    tema: mitos\n    gancho_padrao_id: g1\n"
        "  - rota: tipografico\n    tema: \n    gancho_padrao_id: g2\n"
        "  - rota: foto-local\n    tema: \n    gancho_padrao_id: g3\n"
    )
    out = DiretorCriativo(llm=FakeLLM(responses=[yaml_resp]), temas_disponiveis=["mitos"]).dirigir(
        pautas=pautas, knowledge={}, digest=""
    )
    assert [a.titulo for a in out] == ["a", "b", "c"]
