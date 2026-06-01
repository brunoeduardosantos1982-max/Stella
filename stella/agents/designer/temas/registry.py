"""Registry de temas do formato foto-heroi."""

from __future__ import annotations

from stella.agents.designer.temas.base import TemaRecipe
from stella.agents.designer.temas.impactante import ImpactanteRecipe
from stella.agents.designer.temas.mitos import MitosRecipe
from stella.agents.designer.temas.tech import TechRecipe

TEMAS: dict[str, TemaRecipe] = {
    ImpactanteRecipe.nome: ImpactanteRecipe(),
    MitosRecipe.nome: MitosRecipe(),
    TechRecipe.nome: TechRecipe(),
}


def get_tema(nome: str) -> TemaRecipe:
    if nome not in TEMAS:
        raise KeyError(f"tema desconhecido: {nome!r}")
    return TEMAS[nome]
