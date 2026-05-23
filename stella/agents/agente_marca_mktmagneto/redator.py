"""Redator — gera legenda + hashtags + slides ancorado no briefing da marca."""

from __future__ import annotations

from dataclasses import dataclass, field

import yaml

from stella.adapters.llm.base import LLMProvider

from .planejador import Pauta


@dataclass
class PostTexto:
    """Saída do Redator: pauta + textos prontos para virar post."""

    pilar: int
    titulo: str
    legenda: str = ""
    hashtags: list[str] = field(default_factory=list)
    slides: list[str] = field(default_factory=list)


@dataclass
class Redator:
    """Gera legenda padrão + hashtags + slides a partir de uma Pauta.

    Usa Sonnet (via LLMProvider). O briefing da marca entra no prompt como
    contexto da voz e da estrutura padrão de legenda.
    """

    llm: LLMProvider

    def escrever(self, *, pauta: Pauta, knowledge: dict[str, str]) -> PostTexto:
        prompt = self._montar_prompt(pauta, knowledge)
        resposta = self.llm.complete(prompt).texto
        try:
            dados = yaml.safe_load(resposta) or {}
        except yaml.YAMLError:
            dados = {}
        if not isinstance(dados, dict):
            dados = {}
        return PostTexto(
            pilar=pauta.pilar,
            titulo=pauta.titulo,
            legenda=str(dados.get("legenda", "")).strip(),
            hashtags=[str(h) for h in dados.get("hashtags", [])],
            slides=[str(s) for s in dados.get("slides", [])],
        )

    def _montar_prompt(self, pauta: Pauta, knowledge: dict[str, str]) -> str:
        briefing = knowledge.get("briefing", "")
        return (
            "Você é o Redator do Agente de Marca @mktmagneto.ia.\n"
            "Aplique as skills `copywriting-engajamento-ptbr`, "
            "`carrossel-instagram-ia` e `estrategia-hashtags`.\n\n"
            f"BRIEFING DA MARCA:\n{briefing}\n\n"
            f"PAUTA: pilar {pauta.pilar} — {pauta.titulo}\n\n"
            "Devolva APENAS YAML no formato:\n"
            "legenda: |\n"
            "  🔥 [hook]\n\n  [contexto]\n\n  [corpo]\n\n  👇 [CTA]\n"
            "hashtags:\n"
            "  - <12 a 15 hashtags>\n"
            "slides:\n"
            "  - <texto de cada slide, começando pela capa>\n"
        )
