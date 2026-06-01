"""BriefingCopy + MontadorBriefing - transforma grounding em briefing acionavel de copy."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import yaml

from stella.adapters.llm.base import LLMProvider
from stella.agents.agente_marca_mktmagneto.planejador import _strip_code_fence
from stella.agents.copywriter.ganchos import GanchoCatalog


@dataclass
class BriefingCopy:
    angulo: str = ""
    gancho_padrao_id: str = ""
    gancho_instrucao: str = ""
    pontos_chave: list[str] = field(default_factory=list)
    cta_unico: str = ""
    hashtags_sugeridas: list[str] = field(default_factory=list)


@dataclass
class MontadorBriefing:
    llm: LLMProvider
    ganchos: GanchoCatalog

    def montar(self, *, pauta: dict[str, Any], knowledge_pauta: dict[str, Any]) -> BriefingCopy:
        prompt = self._prompt(pauta, knowledge_pauta)
        resposta = self.llm.complete(prompt).texto
        try:
            dados = yaml.safe_load(_strip_code_fence(resposta)) or {}
        except yaml.YAMLError:
            dados = {}
        if not isinstance(dados, dict):
            dados = {}
        if not dados.get("angulo"):
            return BriefingCopy(angulo=str(pauta.get("titulo", "")))
        return BriefingCopy(
            angulo=str(dados.get("angulo", "")),
            gancho_padrao_id=str(dados.get("gancho_padrao_id", "")),
            gancho_instrucao=str(dados.get("gancho_instrucao", "")),
            pontos_chave=[str(p) for p in dados.get("pontos_chave", []) if str(p).strip()],
            cta_unico=str(dados.get("cta_unico", "")),
            hashtags_sugeridas=[
                str(h) for h in dados.get("hashtags_sugeridas", []) if str(h).strip()
            ],
        )

    def _prompt(self, pauta: dict[str, Any], knowledge_pauta: dict[str, Any]) -> str:
        briefing = knowledge_pauta.get("briefing", "")
        referencia = knowledge_pauta.get("referencia", "")
        padroes = (
            "\n".join(
                f"  - {g.get('id')}: {g.get('estrutura')} (usar: {g.get('quando_usar')})"
                for g in self.ganchos.listar()
            )
            or "  (sem padroes)"
        )
        return (
            "Voce e o Diretor de Copy. Monte um BRIEFING acionavel para o copywriter.\n\n"
            f"PAUTA: pilar {pauta.get('pilar', '')} - {pauta.get('titulo', '')}\n\n"
            f"BRIEFING DA MARCA:\n{briefing}\n\n"
            f"REFERENCIA/GROUNDING (extraia daqui os CONCRETOS a nomear):\n{referencia}\n\n"
            f"PADROES DE GANCHO DISPONIVEIS:\n{padroes}\n\n"
            "Escolha 1 padrao de gancho, extraia os pontos-chave concretos (nomes, dados, "
            "ferramentas), defina 1 CTA so e hashtags coerentes com a referencia.\n\n"
            "Devolva APENAS YAML:\n"
            "angulo: <angulo editorial>\n"
            "gancho_padrao_id: <id do padrao>\n"
            "gancho_instrucao: <como aplicar a esta pauta>\n"
            "pontos_chave: [<concretos a nomear>]\n"
            "cta_unico: <um CTA>\n"
            "hashtags_sugeridas: [<hashtags>]\n"
        )
