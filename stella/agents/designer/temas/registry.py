"""Registry de temas do formato foto-heroi."""

from __future__ import annotations

from stella.agents.designer.temas.automatizacao import AutomatizacaoRecipe
from stella.agents.designer.temas.autoridade import AutoridadeRecipe
from stella.agents.designer.temas.base import TemaRecipe
from stella.agents.designer.temas.dicas import DicasRecipe
from stella.agents.designer.temas.ferramentas import FerramentasRecipe
from stella.agents.designer.temas.impactante import ImpactanteRecipe
from stella.agents.designer.temas.mitos import MitosRecipe
from stella.agents.designer.temas.segredos import SegredosRecipe
from stella.agents.designer.temas.tech import TechRecipe

TEMAS: dict[str, TemaRecipe] = {
    AutomatizacaoRecipe.nome: AutomatizacaoRecipe(),
    AutoridadeRecipe.nome: AutoridadeRecipe(),
    DicasRecipe.nome: DicasRecipe(),
    FerramentasRecipe.nome: FerramentasRecipe(),
    ImpactanteRecipe.nome: ImpactanteRecipe(),
    MitosRecipe.nome: MitosRecipe(),
    SegredosRecipe.nome: SegredosRecipe(),
    TechRecipe.nome: TechRecipe(),
}


def get_tema(nome: str) -> TemaRecipe:
    if nome not in TEMAS:
        raise KeyError(f"tema desconhecido: {nome!r}")
    return TEMAS[nome]
