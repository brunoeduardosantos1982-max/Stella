"""MontadorVisual — preenche templates HTML do kit e renderiza para PNG."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from stella.adapters.vault.base import VaultRepository

from .redator import PostTexto


class RenderProtocol(Protocol):
    """Contrato mínimo de um renderizador HTML → PNG."""

    def render_png(self, html: str, width: int, height: int) -> bytes: ...


_TEMPLATE_CAPA = "C04 Claude Obsidian/outputs/mktmagneto-ia/templates/capa-carrossel.html"
_INSTAGRAM_4_5 = (1080, 1350)


@dataclass
class MontadorVisual:
    """Preenche o template HTML da capa do carrossel com o texto do post
    e renderiza para PNG (1080×1350) via Playwright (ou Fake nos testes)."""

    vault: VaultRepository
    render: RenderProtocol

    def montar(self, post: PostTexto, post_id: str) -> bytes:
        try:
            template = self.vault.read_note(_TEMPLATE_CAPA).content
        except FileNotFoundError as e:
            raise FileNotFoundError(f"template visual ausente em {_TEMPLATE_CAPA}") from e

        html = template.replace("{{TITULO}}", post.titulo).replace("{{LEGENDA}}", post.legenda)
        # post_id reservado para escrita do arquivo (Task 17/19);
        # MontadorVisual só renderiza e devolve bytes.
        _ = post_id
        return self.render.render_png(html, *_INSTAGRAM_4_5)
