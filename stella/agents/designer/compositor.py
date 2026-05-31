"""HtmlCompositor - recipe de tema + conteudo + imagem heroi -> PNG no vault."""

from __future__ import annotations

import base64
from dataclasses import dataclass

from stella.adapters.render.html_renderer import HtmlRenderer
from stella.adapters.vault.base import VaultRepository
from stella.agents.designer.temas.base import FotoHeroContent
from stella.agents.designer.temas.registry import get_tema

_DIR = "C04 Claude Obsidian/outputs/mktmagneto-ia/imagens"


@dataclass
class HtmlCompositor:
    renderer: HtmlRenderer
    vault: VaultRepository

    def compor(
        self, tema: str, c: FotoHeroContent, hero_bytes: bytes, *, post_id: str, idx: int
    ) -> str:
        data_uri = "data:image/png;base64," + base64.b64encode(hero_bytes).decode("ascii")
        html = get_tema(tema).html(c, data_uri)
        png = self.renderer.render(html, width=1080, height=1350)
        rel = f"{_DIR}/{post_id}/hero{idx}.png"
        self.vault.write_binary(rel, png)
        return rel
