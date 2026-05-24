"""Planejador — escolhe 3 pautas da semana via LLM, ancorado em briefing + calendário."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import yaml

from stella.adapters.llm.base import LLMProvider

_FENCE_RE = re.compile(r"^```[a-z]*\n?(.*?)\n?```\s*$", re.DOTALL)


def _strip_code_fence(text: str) -> str:
    m = _FENCE_RE.match(text.strip())
    return m.group(1) if m else text


@dataclass
class Pauta:
    """Pauta selecionada para a semana — saída do Planejador."""

    pilar: int
    titulo: str


@dataclass
class Planejador:
    """Seleciona 3 pautas da semana respeitando mix 50/25/25 e evitando repetição.

    Usa um LLM (Sonnet recomendado) que recebe os pilares disponíveis, o digest
    de tendências e a lista de títulos já planejados/publicados no calendário,
    e devolve 3 pautas em YAML.
    """

    llm: LLMProvider

    def planejar(
        self,
        *,
        pilares_briefing: list[int],
        digest: list[dict[str, Any]],
        calendario_atual: list[dict[str, Any]],
    ) -> list[Pauta]:
        titulos_evitar = [c.get("titulo", "") for c in calendario_atual]
        prompt = self._montar_prompt(pilares_briefing, digest, titulos_evitar)
        resposta = self.llm.complete(prompt).texto
        try:
            dados = yaml.safe_load(_strip_code_fence(resposta)) or {}
        except yaml.YAMLError:
            return []
        if not isinstance(dados, dict):
            return []
        pautas_raw = dados.get("pautas", [])
        pautas: list[Pauta] = []
        for p in pautas_raw[:3]:  # corta no máximo 3
            try:
                pautas.append(Pauta(pilar=int(p["pilar"]), titulo=str(p["titulo"])))
            except (KeyError, TypeError, ValueError):
                continue
        return pautas

    def _montar_prompt(
        self,
        pilares: list[int],
        digest: list[dict[str, Any]],
        evitar: list[str],
    ) -> str:
        return (
            "Você é o Planejador do Agente de Marca @mktmagneto.ia.\n"
            "Aplique a skill `planejamento-editorial`.\n\n"
            "Selecione 3 pautas para a próxima semana, respeitando o mix:\n"
            "  ~50% topo amplo (pilares 1 e 2)\n"
            "  ~25% nicho (pilar 3)\n"
            "  ~25% prova (pilar 4)\n\n"
            f"Pilares disponíveis (numerados): {pilares}\n"
            f"Tendências detectadas (digest): {digest}\n"
            f"Títulos a EVITAR (já publicado/planejado no calendário): {evitar}\n\n"
            "Responda APENAS em YAML, no formato:\n"
            "pautas:\n"
            "  - pilar: <int>\n"
            "    titulo: <str>\n"
            "  - ...\n"
        )
