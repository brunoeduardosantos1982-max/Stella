"""Regressão: as queries de pesquisa devem estar ancoradas no nicho da marca.

Bug original: o coordenador pesquisava com `f"pilar {p}"` → queries viravam
"pilar 1 tendências 2026", sem nicho nenhum. O Tavily devolvia tendências
genéricas (decoração/Japandi) e o digest contaminava o planejamento.
"""

from stella.agents.agente_marca_mktmagneto.agent import _NICHO, _queries_pesquisa
from stella.agents.agente_marca_mktmagneto.pesquisador import Pesquisador
from stella.framework.testing.fakes import FakeMCP


def test_queries_pesquisa_ancoradas_no_nicho() -> None:
    queries = _queries_pesquisa()
    assert queries, "deve gerar ao menos uma query"
    for q in queries:
        assert _NICHO in q, f"query sem âncora de nicho: {q!r}"
    # nunca a query semanticamente vazia "pilar N"
    assert not any(q.strip().lower().startswith("pilar ") for q in queries)


def test_pesquisador_recebe_queries_de_nicho() -> None:
    mcp = FakeMCP(nome="tavily", category="research", resultados={})
    Pesquisador(research_mcps=[mcp]).pesquisar(pilares=_queries_pesquisa())
    assert mcp.calls, "o MCP deveria ter sido chamado"
    for chamada in mcp.calls:
        baixa = chamada.lower()
        assert "marketing" in baixa or "vendas" in baixa, f"query fora do nicho: {chamada!r}"
