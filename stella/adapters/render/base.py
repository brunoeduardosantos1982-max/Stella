"""Contrato/erros do adapter de render."""

from __future__ import annotations


class RenderError(Exception):
    """Falha ao renderizar HTML em imagem (browser ausente, exit!=0, timeout)."""
