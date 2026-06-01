"""ResolvedorTipografico - renderiza slides tipograficos/foto-local via HtmlRenderer."""

from __future__ import annotations

import base64
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from stella.adapters.render.html_renderer import HtmlRenderer
from stella.adapters.vault.base import VaultRepository

if TYPE_CHECKING:
    from stella.agents.designer.spec import DesignSpec, SlideSpec

_TEMPLATES = "C04 Claude Obsidian/outputs/mktmagneto-ia/templates"
_FOTOS = "A03 Banco de Imagens/FotosBruno"
_FILA = "C04 Claude Obsidian/Stella-publicacao/fila"
_PH = re.compile(r"\{\{([A-Z0-9_]+)\}\}")


@dataclass
class ResolvedorTipografico:
    renderer: HtmlRenderer
    vault: VaultRepository

    def resolver(self, spec: DesignSpec, *, post_id: str) -> list[str]:
        avisos: list[str] = []
        for slide in spec.slides:
            if slide.foto_hero or (slide.foto and slide.foto.startswith(_FILA)):
                continue
            try:
                html = self._preencher(self._template(slide.template), slide)
                png = self.renderer.render(html, width=1080, height=1350)
                rel = f"{_FILA}/{post_id}/slide-{slide.index:02d}.png"
                self.vault.write_binary(rel, png)
                slide.foto = rel
            except Exception as e:  # noqa: BLE001 - falha isolada por slide
                avisos.append(f"slide {slide.index} (tipografico/{slide.template}): {e}")
        return avisos

    def _template(self, nome: str | None) -> str:
        for cand in (f"{_TEMPLATES}/{nome}.html", f"{_TEMPLATES}/capa-carrossel.html"):
            try:
                return self.vault.read_binary(cand).decode("utf-8")
            except FileNotFoundError:
                continue
        raise FileNotFoundError(f"template {nome!r} e fallback ausentes")

    def _preencher(self, tpl: str, slide: SlideSpec) -> str:
        conteudo: dict[str, Any] = slide.conteudo or {}
        html = tpl
        foto = slide.foto
        if foto:
            caminho = foto if "/" in foto else f"{_FOTOS}/{foto}"
            try:
                dados = self.vault.read_binary(caminho)
                html = html.replace(
                    "{{FOTO_BASE64}}", base64.b64encode(dados).decode("ascii")
                ).replace("{{FOTO_MIME}}", "image/jpeg")
            except FileNotFoundError:
                pass
        return _PH.sub(lambda m: str(conteudo.get(m.group(1).lower(), "")), html)
