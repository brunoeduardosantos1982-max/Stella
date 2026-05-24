"""Copywriter — especialista stateless que produz copy para qualquer marca."""

from __future__ import annotations

from typing import Any

import yaml

from stella.agents.agente_marca_mktmagneto.planejador import _strip_code_fence
from stella.framework.agent import Agent as BaseAgent
from stella.framework.agent import AgentOutput


class Agent(BaseAgent):
    """Especialista de copy: recebe knowledge_pack + pauta, devolve copy completa."""

    def execute(self, input: dict[str, Any]) -> AgentOutput:
        knowledge_pack = input.get("knowledge_pack")
        pauta = input.get("pauta")

        if not knowledge_pack:
            return AgentOutput(
                resultado={},
                sucesso=False,
                mensagens=["knowledge_pack ausente no payload"],
            )
        if not pauta:
            return AgentOutput(
                resultado={},
                sucesso=False,
                mensagens=["pauta ausente no payload"],
            )
        if self._llm is None:
            return AgentOutput(
                resultado={},
                sucesso=False,
                mensagens=["LLM não injetado no copywriter"],
            )

        prompt = self._montar_prompt(
            knowledge_pack,
            pauta,
            input.get("feedback_anterior"),
            input.get("output_anterior"),
        )
        resposta = self._llm.select(complexity="high").complete(prompt).texto

        try:
            dados = yaml.safe_load(_strip_code_fence(resposta)) or {}
        except yaml.YAMLError:
            dados = {}

        if not isinstance(dados, dict):
            dados = {}

        legenda = str(dados.get("legenda", "")).strip()
        slides = [str(s) for s in dados.get("slides", [])]
        hashtags = [str(h) for h in dados.get("hashtags", [])]
        rationale = str(dados.get("rationale", "")).strip()

        sucesso = bool(legenda)
        return AgentOutput(
            resultado={
                "legenda": legenda,
                "slides": slides,
                "hashtags": hashtags,
                "rationale": rationale,
            },
            sucesso=sucesso,
            mensagens=[] if sucesso else ["LLM não retornou legenda válida"],
        )

    def _montar_prompt(
        self,
        knowledge_pack: dict[str, Any],
        pauta: dict[str, Any],
        feedback_anterior: str | None,
        output_anterior: dict[str, Any] | None,
    ) -> str:
        voz = knowledge_pack.get("voz", "")
        cta = knowledge_pack.get("cta_padrao", "")
        hashtags_base = knowledge_pack.get("hashtags_base", [])
        pilar = pauta.get("pilar", "")
        titulo = pauta.get("titulo", "")
        tipo = pauta.get("tipo", "carrossel")
        n_slides = pauta.get("n_slides", 3)

        partes = [
            "Você é o Copywriter do Time de Marketing.",
            "Aplique as skills `copywriting-engajamento-ptbr`, `carrossel-instagram-ia` e `estrategia-hashtags`.",
            "",
            f"VOZ DA MARCA: {voz}",
            f"CTA PADRÃO: {cta}",
            f"HASHTAGS BASE: {hashtags_base}",
            "",
            f"PAUTA: pilar {pilar} — {titulo}",
            f"FORMATO: {tipo}, {n_slides} slides",
        ]

        if feedback_anterior:
            output_ant_str = str(output_anterior) if output_anterior else ""
            partes += [
                "",
                "FEEDBACK DO REVISOR (iteração anterior):",
                feedback_anterior,
                "OUTPUT ANTERIOR:",
                output_ant_str,
                "Incorpore o feedback acima na nova versão.",
            ]

        partes += [
            "",
            "Devolva APENAS YAML no formato:",
            "legenda: |",
            "  🔥 [hook]",
            "",
            "  [corpo]",
            "",
            "  👇 [CTA]",
            "slides:",
            "  - [texto de cada slide]",
            "hashtags:",
            "  - [12 a 15 hashtags]",
            "rationale: [técnica aplicada]",
        ]

        return "\n".join(partes)
