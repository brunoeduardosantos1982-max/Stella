"""TavilyClient — adapter HTTP real para Tavily Search API.

Implementa o contrato _MCPInvocavel (nome + invoke) herdando ConexaoMCP,
para ser registrado em MCPRegistry como MCP de category: research.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from stella.domain.conexao_mcp import ConexaoMCP

_TAVILY_ENDPOINT = "https://api.tavily.com/search"
_TIMEOUT_S = 15
_MAX_RESULTS = 5


@dataclass
class TavilyClient(ConexaoMCP):
    """Wrapper httpx para Tavily Search API. Primário da cascata de pesquisa."""

    api_key: str = ""

    def invoke(self, query: str) -> list[dict[str, Any]]:
        """Busca `query` no Tavily e devolve lista de {titulo, snippet, url}."""
        resp = httpx.post(
            _TAVILY_ENDPOINT,
            json={"api_key": self.api_key, "query": query, "max_results": _MAX_RESULTS},
            timeout=_TIMEOUT_S,
        )
        resp.raise_for_status()
        return [
            {
                "titulo": r.get("title", ""),
                "snippet": r.get("content", ""),
                "url": r.get("url", ""),
            }
            for r in resp.json().get("results", [])
        ]
