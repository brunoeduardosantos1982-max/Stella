"""Contrato das recipes de tema do formato foto-heroi."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class FotoHeroContent:
    headline: str
    sublabel: str | None = None
    label_topo: str | None = None
    anotacoes: list[str] = field(default_factory=list)
    logos: list[str] = field(default_factory=list)
    counter: str | None = None


class TemaRecipe(Protocol):
    nome: str
    usa_soul: bool

    def hf_prompt(self) -> str: ...

    def html(self, c: FotoHeroContent, hero_data_uri: str) -> str: ...
