"""Pesquisador — cascata Brave → Perplexity → ... → digest vazio."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Protocol


class _MCPInvocavel(Protocol):
    """Contrato mínimo de um MCP de pesquisa para o Pesquisador.

    Compatível com FakeMCP e ConexaoMCP real (quando tiver `invoke`).
    """

    nome: str

    def invoke(self, chave: str) -> list[dict[str, Any]]: ...


@dataclass
class Pesquisador:
    """Cascata de pesquisa: tenta MCPs em ordem; primeiro com resultado vence.

    `research_mcps` é a lista ordenada (primário → fallback → ...) — em produção
    vem de `MCPRegistry.list_by_category("research")` (Brave primeiro, Perplexity
    depois, conforme registrado em build_stella).
    """

    research_mcps: list[_MCPInvocavel]
    logger: logging.Logger | None = None

    def pesquisar(self, pilares: list[str]) -> list[dict[str, Any]]:
        """Devolve digest agregado. Se todos os MCPs falharem, lista vazia."""
        queries = self._queries_dos_pilares(pilares)
        for mcp in self.research_mcps:
            agregado: list[dict[str, Any]] = []
            try:
                for q in queries:
                    agregado.extend(mcp.invoke(q))
            except Exception as e:  # noqa: BLE001 — cascata: qualquer falha → próximo
                self._log(f"MCP {mcp.nome} falhou ({e!r}); caindo para próximo")
                continue
            if agregado:
                return agregado
        return []

    def _queries_dos_pilares(self, pilares: list[str]) -> list[str]:
        return [f"{pilar} tendências 2026" for pilar in pilares]

    def _log(self, msg: str) -> None:
        if self.logger is not None:
            self.logger.warning(msg)
