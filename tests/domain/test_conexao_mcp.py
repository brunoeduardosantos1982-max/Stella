from stella.domain.conexao_mcp import ConexaoMCP, StatusMCP


def test_conexao_mcp_estrutura():
    c = ConexaoMCP(
        nome="brave-search",
        tipo="http",
        endpoint="https://api.search.brave.com",
        status=StatusMCP.PRE_CONFIGURADO,
        ferramentas_expostas=["web_search"],
        requer_modelo="sonnet",
    )
    assert c.status == StatusMCP.PRE_CONFIGURADO
    assert "web_search" in c.ferramentas_expostas


def test_status_mcp_valores():
    assert StatusMCP.PRE_CONFIGURADO.value == "pre-configurado"
    assert StatusMCP.POR_DEMANDA.value == "por-demanda"
