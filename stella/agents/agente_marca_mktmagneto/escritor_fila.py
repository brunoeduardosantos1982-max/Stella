"""EscritorFila — grava o post pronto na fila do agente_publicador (Sub-projeto B)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from stella.adapters.vault.base import VaultRepository

from .redator import PostTexto

_FILA_DIR = "C04 Claude Obsidian/Stella-publicacao/fila"


@dataclass
class EscritorFila:
    """Grava .md (frontmatter no formato do publicador) + .png na fila."""

    vault: VaultRepository

    def escrever(
        self,
        post: PostTexto,
        *,
        post_id: str,
        png_bytes: bytes,
        agendar_para: datetime,
    ) -> str:
        """Retorna o path da nota .md escrita."""
        md_path = f"{_FILA_DIR}/{post_id}.md"
        png_path = f"{_FILA_DIR}/{post_id}.png"

        # 1. PNG (binário)
        self.vault.write_binary(png_path, png_bytes)

        # 2. Frontmatter no formato esperado pelo agente_publicador
        frontmatter: dict[str, Any] = {
            "marca": "mktmagneto",
            "plataformas": ["instagram"],
            "tipo-post": "feed",
            "agendar-para": agendar_para.strftime("%Y-%m-%d %H:%M"),
            "status": "rascunho",
            "imagem": f"{post_id}.png",
        }

        # 3. Corpo = legenda + hashtags em linha separada
        corpo = post.legenda + "\n\n" + " ".join(post.hashtags)
        self.vault.write_note(md_path, corpo, frontmatter)

        return md_path
