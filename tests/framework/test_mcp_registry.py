import pytest

from stella.domain.conexao_mcp import ConexaoMCP
from stella.framework.errors import MCPNotFoundError
from stella.framework.resources.mcp_registry import MCPRegistry


def _mcp(nome: str, categoria: str | None = None) -> ConexaoMCP:
    return ConexaoMCP(
        nome=nome,
        tipo="http",
        endpoint=f"http://localhost/{nome}",
        category=categoria,
    )


def test_mcp_registry_vazio_no_inicio() -> None:
    reg = MCPRegistry()
    assert reg.list_all() == []


def test_mcp_registry_register_e_get() -> None:
    reg = MCPRegistry()
    brave = _mcp("brave-search", categoria="research")
    reg.register(brave)
    assert reg.get("brave-search") is brave


def test_mcp_registry_get_levanta_mcp_not_found() -> None:
    reg = MCPRegistry()
    with pytest.raises(MCPNotFoundError, match="brave-search"):
        reg.get("brave-search")


def test_mcp_registry_register_duplicado_sobrescreve() -> None:
    """Registrar com mesmo nome sobrescreve — util para hot-reload em dev."""
    reg = MCPRegistry()
    reg.register(_mcp("brave-search", categoria="research"))
    reg.register(_mcp("brave-search", categoria="automation"))
    assert reg.get("brave-search").category == "automation"


def test_mcp_registry_list_all_retorna_todos() -> None:
    reg = MCPRegistry()
    reg.register(_mcp("a"))
    reg.register(_mcp("b"))
    reg.register(_mcp("c"))
    nomes = {m.nome for m in reg.list_all()}
    assert nomes == {"a", "b", "c"}


def test_mcp_registry_list_by_category_filtra_por_categoria() -> None:
    """HOOK Sub-projeto F: lista MCPs por categoria (research, automation, data)."""
    reg = MCPRegistry()
    reg.register(_mcp("brave-search", categoria="research"))
    reg.register(_mcp("perplexity", categoria="research"))
    reg.register(_mcp("n8n", categoria="automation"))
    reg.register(_mcp("sem-categoria"))

    research = {m.nome for m in reg.list_by_category("research")}
    automation = {m.nome for m in reg.list_by_category("automation")}
    inexistente = reg.list_by_category("data")

    assert research == {"brave-search", "perplexity"}
    assert automation == {"n8n"}
    assert inexistente == []


def test_mcp_registry_list_by_category_ignora_mcps_sem_categoria() -> None:
    reg = MCPRegistry()
    reg.register(_mcp("sem-categoria"))
    assert reg.list_by_category("research") == []
