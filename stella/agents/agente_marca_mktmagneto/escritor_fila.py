"""EscritorFila — grava nota placeholder na fila (renderização via Paper MCP depois)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from stella.adapters.vault.base import VaultRepository
from stella.domain.post import PostTexto

_FILA_DIR = "C04 Claude Obsidian/Stella-publicacao/fila"


@dataclass
class EscritorFila:
    """Grava .md de placeholder na fila (PNG gerado na Fase 2 pelo Paper MCP)."""

    vault: VaultRepository

    def escrever(
        self,
        post: PostTexto,
        *,
        post_id: str,
        design_spec_path: str,
        agendar_para: datetime,
        status: str = "pending_render",
        qa_warnings: list[str] | None = None,
    ) -> str:
        """Retorna o path da nota .md escrita."""
        md_path = f"{_FILA_DIR}/{post_id}.md"

        frontmatter: dict[str, Any] = {
            "marca": "mktmagneto",
            "plataformas": ["instagram"],
            "tipo-post": "feed",
            "agendar-para": agendar_para.strftime("%Y-%m-%d %H:%M"),
            "status": status,
            "design_spec": design_spec_path,
            "imagens": [],
        }
        if qa_warnings:
            frontmatter["qa_warnings"] = qa_warnings

        corpo = post.legenda + "\n\n" + " ".join(post.hashtags)
        self.vault.write_note(md_path, corpo, frontmatter)
        return md_path
