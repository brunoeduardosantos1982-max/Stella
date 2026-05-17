"""MCPRegistry — indice in-memory de conexoes MCP disponiveis.

MCPs sao registradas explicitamente via register() (sem auto-discovery em
FB-M2). O metodo list_by_category e o HOOK do Sub-projeto F (Web Research
+ Curiosidade): permite a Stella perguntar 'quais MCPs de pesquisa tenho?'
sem hardcoding de nomes.
"""

from __future__ import annotations

from stella.domain.conexao_mcp import ConexaoMCP
from stella.framework.errors import MCPNotFoundError


class MCPRegistry:
    """Indice de conexoes MCP para injecao em agentes via builder."""

    def __init__(self) -> None:
        self._por_nome: dict[str, ConexaoMCP] = {}

    def register(self, mcp: ConexaoMCP) -> None:
        """Registra (ou sobrescreve) uma conexao MCP indexada pelo nome."""
        self._por_nome[mcp.nome] = mcp

    def get(self, nome: str) -> ConexaoMCP:
        if nome not in self._por_nome:
            raise MCPNotFoundError(f"MCP '{nome}' nao registrada")
        return self._por_nome[nome]

    def list_all(self) -> list[ConexaoMCP]:
        return list(self._por_nome.values())

    def list_by_category(self, category: str) -> list[ConexaoMCP]:
        """HOOK Sub-projeto F: lista MCPs por categoria declarada.

        Categorias comuns esperadas: 'research', 'automation', 'data',
        'communication'. MCPs sem `category` ficam de fora.
        """
        return [mcp for mcp in self._por_nome.values() if mcp.category == category]
