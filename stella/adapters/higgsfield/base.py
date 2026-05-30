"""Contrato e erros do adapter Higgsfield."""

from __future__ import annotations

from typing import Protocol


class HiggsFieldError(Exception):
    """Erro do adapter Higgsfield (API, timeout, falha de geração)."""


class HiggsFieldClient(Protocol):
    def generate_image(self, prompt: str, soul_id: str | None = None) -> str:
        """Gera imagem com Soul ID e retorna URL pública.

        Args:
            prompt: Descrição da cena/estilo.
            soul_id: ID do perfil Soul ID (opcional — usa padrão da conta).

        Returns:
            URL da imagem gerada (acessível via HTTP GET).

        Raises:
            HiggsFieldError: API indisponível, token inválido ou geração falhou.
        """
        ...
