"""ResolvedorFotoHero - materializa slides foto-hero (cena HF + composicao HTML)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from stella.adapters.higgsfield.base import HiggsFieldClient
from stella.adapters.higgsfield.resolvedor import _baixar_http
from stella.agents.designer.compositor import HtmlCompositor
from stella.agents.designer.temas.base import FotoHeroContent
from stella.agents.designer.temas.registry import get_tema

if TYPE_CHECKING:
    from stella.agents.designer.spec import DesignSpec

# A imagem do herói é só FUNDO — toda a tipografia entra via composição HTML.
# Sem isto o Higgsfield "assa" texto falso/embolado na foto (gibberish no meio).
_SEM_TEXTO = (
    " Sem nenhum texto, letra, palavra, número, legenda ou marca d'água na imagem; "
    "apenas a cena fotográfica."
)


@dataclass
class ResolvedorFotoHero:
    higgs: HiggsFieldClient
    compositor: HtmlCompositor
    baixar: Callable[[str], bytes] = field(default=_baixar_http)

    def resolver(self, spec: DesignSpec, *, post_id: str) -> list[str]:
        avisos: list[str] = []
        for slide in spec.slides:
            if not slide.foto_hero or not slide.tema or slide.foto:
                continue
            try:
                recipe = get_tema(slide.tema)
                prompt = recipe.hf_prompt() + _SEM_TEXTO
                url = (
                    self.higgs.generate_image(prompt)
                    if recipe.usa_soul
                    else self.higgs.generate_image(prompt, soul_id="")
                )
                hero = self.baixar(url)
                c = _foto_hero_content(slide.foto_hero)
                slide.foto = self.compositor.compor(
                    slide.tema, c, hero, post_id=post_id, idx=slide.index
                )
            except Exception as e:  # noqa: BLE001 - falha isolada por slide
                avisos.append(f"slide {slide.index} (foto-hero/{slide.tema}): {e}")
        return avisos


def _lista_str(valor: object) -> list[str]:
    if not isinstance(valor, list):
        return []
    return [str(item) for item in valor]


def _foto_hero_content(dados: dict[str, object]) -> FotoHeroContent:
    return FotoHeroContent(
        headline=str(dados.get("headline", "")),
        sublabel=str(dados["sublabel"]) if dados.get("sublabel") is not None else None,
        label_topo=str(dados["label_topo"]) if dados.get("label_topo") is not None else None,
        anotacoes=_lista_str(dados.get("anotacoes")),
        logos=_lista_str(dados.get("logos")),
        counter=str(dados["counter"]) if dados.get("counter") is not None else None,
    )
