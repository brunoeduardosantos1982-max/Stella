"""TavilyClient — adapter HTTP real para Tavily Search API.

Implementa o contrato _MCPInvocavel (nome + invoke) herdando ConexaoMCP,
para ser registrado em MCPRegistry como MCP de category: research.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

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


def buscar_noticias_tavily(
    query: str,
    api_key: str,
    *,
    days: int = 2,
    max_results: int = 10,
    include_domains: list[str] | None = None,
    http_post: Callable[..., Any] = httpx.post,
) -> list[dict[str, Any]]:
    """Busca notícias recentes no Tavily (topic=news) e normaliza os campos.

    `include_domains` enviesa a busca para a allowlist curada (híbrido A+B).
    """
    payload: dict[str, Any] = {
        "api_key": api_key,
        "query": query,
        "topic": "news",
        "days": days,
        "max_results": max_results,
    }
    if include_domains:
        payload["include_domains"] = include_domains

    resp = http_post(_TAVILY_ENDPOINT, json=payload, timeout=_TIMEOUT_S)
    resp.raise_for_status()
    resultados = resp.json().get("results", [])
    itens: list[dict[str, Any]] = []
    for r in resultados:
        url = r.get("url", "")
        itens.append(
            {
                "titulo": r.get("title", ""),
                "url": url,
                "veiculo": urlparse(url).netloc.removeprefix("www."),
                "snippet": r.get("content", ""),
                "data": r.get("published_date", ""),
            }
        )
    return itens
