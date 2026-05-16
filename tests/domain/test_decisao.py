from datetime import date

from stella.domain.decisao import Decisao


def test_decisao_estrutura():
    d = Decisao(
        id="2026-05-14-001",
        titulo="Usar Brave Search",
        contexto="Precisávamos de busca web barata",
        decisao="Adotar Brave Search MCP",
        motivo="Grátis até 2k queries/mês",
        data=date(2026, 5, 14),
    )
    assert d.titulo == "Usar Brave Search"
    assert d.data == date(2026, 5, 14)
