"""HtmlCompositor - recipe de tema + conteudo + imagem heroi -> PNG no vault."""

from __future__ import annotations

import base64
import io
from dataclasses import dataclass

from PIL import Image

from stella.adapters.render.html_renderer import HtmlRenderer
from stella.adapters.vault.base import VaultRepository
from stella.agents.designer.temas.base import FotoHeroContent
from stella.agents.designer.temas.registry import get_tema

# Arte final do foto-hero vai p/ a fila do post (mesmo lugar do tipográfico) —
# assim `fila/<post_id>/` é o balcão único com TODA a arte, qualquer que seja a rota.
_FILA = "C04 Claude Obsidian/Stella-publicacao/fila"


def _downscale(png_bytes: bytes, *, largura: int = 1080) -> bytes:
    """Reduz a largura da imagem p/ <=`largura` antes de embutir em base64.

    Best-effort: se os bytes nao forem uma imagem decodificavel, devolve-os
    intactos (downscale e otimizacao de peso, nunca correcao)."""
    try:
        img = Image.open(io.BytesIO(png_bytes))
        img.load()
    except Exception:  # noqa: BLE001 — passthrough: bytes nao-imagem seguem intactos
        return png_bytes
    if img.width <= largura:
        return png_bytes
    altura = round(img.height * largura / img.width)
    rgb = img.convert("RGB").resize((largura, altura), Image.Resampling.LANCZOS)
    out = io.BytesIO()
    rgb.save(out, format="PNG", optimize=True)
    return out.getvalue()


@dataclass
class HtmlCompositor:
    renderer: HtmlRenderer
    vault: VaultRepository

    def compor(
        self, tema: str, c: FotoHeroContent, hero_bytes: bytes, *, post_id: str, idx: int
    ) -> str:
        hero_bytes = _downscale(hero_bytes)
        data_uri = "data:image/png;base64," + base64.b64encode(hero_bytes).decode("ascii")
        html = get_tema(tema).html(c, data_uri)
        png = self.renderer.render(html, width=1080, height=1350)
        rel = f"{_FILA}/{post_id}/slide-{idx:02d}.png"
        self.vault.write_binary(rel, png)
        return rel
