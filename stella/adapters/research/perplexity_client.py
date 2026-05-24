"""PerplexityClient — adapter HTTP real para Perplexity API.

Fallback da cascata de pesquisa. Usa endpoint chat/completions com
modelo sonar (otimizado para web-search com citações).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from stella.domain.conexao_mcp import ConexaoMCP

_PERPLEXITY_ENDPOINT = "https://api.perplexity.ai/chat/completions"
_MODEL = "sonar"
_TIMEOUT_S = 20


@dataclass
class PerplexityClient(ConexaoMCP):
    """Wrapper httpx para Perplexity chat/completions com busca web."""

    api_key: str = ""

    def invoke(self, query: str) -> list[dict[str, Any]]:
        """Envia `query` ao Perplexity e devolve lista de {titulo, snippet}."""
        resp = httpx.post(
            _PERPLEXITY_ENDPOINT,
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={
                "model": _MODEL,
                "messages": [{"role": "user", "content": query}],
            },
            timeout=_TIMEOUT_S,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
        return [{"titulo": query, "snippet": content, "url": ""}]
