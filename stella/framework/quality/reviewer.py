"""QualityReviewer — Stella supervisora dos agentes (Q2=E loop).

Esta classe orquestra a revisao de qualidade. Decisoes:
- Q1=C: ReviewPolicy (em policies.py) decide SE revisar.
- Q2=E: combinacao — refaz 1x, depois aceita com aviso (Task 10).
- Q3=C: padroes hibridos — declarados em C04/Padroes/ + Stella aprende (FeedbackLogger em feedback.py).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Literal, get_args

from stella.adapters.llm.router import LLMRouter
from stella.adapters.vault.base import VaultRepository
from stella.domain.enums import ModeloIA
from stella.framework.agent import AgentOutput
from stella.framework.manifest import AgentManifest
from stella.framework.quality.policies import ReviewPolicy
from stella.framework.resources.skills_registry import SkillsRegistry

Veredicto = Literal["aprovado", "refazer", "aceitar_com_aviso", "rejeitar"]

_PADRAO_PATH_TEMPLATE = "C04 Claude Obsidian/Padrões/{nome}.md"


@dataclass
class ReviewResult:
    """Resultado da revisao de qualidade.

    Atributos:
        veredicto: 'aprovado' | 'refazer' | 'aceitar_com_aviso' | 'rejeitar'.
        feedback: texto em PT-BR explicando a decisao.
        output_final: AgentOutput entregue ao caller.
        avisos_para_bruno: mensagens em tom Jarvis a passar ao usuario.
    """

    veredicto: Veredicto
    feedback: str
    output_final: AgentOutput
    avisos_para_bruno: list[str] = field(default_factory=list)


class QualityReviewer:
    """Aplica revisao de qualidade no output de cada agente."""

    def __init__(
        self,
        llm: LLMRouter | None,
        vault: VaultRepository | None,
        skills_reg: SkillsRegistry | None,
        policy: ReviewPolicy,
    ) -> None:
        self._llm = llm
        self._vault = vault
        self._skills_reg = skills_reg
        self._policy = policy

    def review(
        self,
        input_original: dict[str, Any],
        output: AgentOutput,
        agent_manifest: AgentManifest,
        tentativa: int = 1,
    ) -> ReviewResult:
        if not self._policy.deve_revisar(agent_manifest, input_original):
            return ReviewResult(
                veredicto="aprovado",
                feedback="revisao pulada por politica (ReviewPolicy)",
                output_final=output,
            )

        veredicto, feedback = self._avaliar_via_llm(input_original, output, agent_manifest)

        # Q2=E: se refazer na 2a+ tentativa, converte para aceitar_com_aviso
        # para nao travar o Bruno indefinidamente.
        if veredicto == "refazer" and tentativa >= 2:
            aviso = (
                f"Senhor, {agent_manifest.nome} tentou 2x e ainda esta fora do padrao: {feedback}"
            )
            return ReviewResult(
                veredicto="aceitar_com_aviso",
                feedback=feedback,
                output_final=output,
                avisos_para_bruno=[aviso],
            )

        return ReviewResult(veredicto=veredicto, feedback=feedback, output_final=output)

    def _avaliar_via_llm(
        self,
        input_original: dict[str, Any],
        output: AgentOutput,
        manifest: AgentManifest,
    ) -> tuple[Veredicto, str]:
        if self._llm is None:
            return ("rejeitar", "LLM nao configurado no QualityReviewer")

        padrao = self._read_opcional(_PADRAO_PATH_TEMPLATE.format(nome=manifest.setor))
        aprendizados = self._read_opcional(_PADRAO_PATH_TEMPLATE.format(nome="_aprendizados"))

        prompt = self._montar_prompt(
            input_original=input_original,
            output=output,
            manifest=manifest,
            padrao=padrao,
            aprendizados=aprendizados,
        )

        provider = self._llm.with_minimum(ModeloIA.SONNET).select(complexity="high")
        resposta = provider.complete(prompt)
        return self._parsear_resposta(resposta.texto)

    def _read_opcional(self, path: str) -> str:
        if self._vault is None:
            return ""
        try:
            return self._vault.read_note(path).content
        except (FileNotFoundError, PermissionError):
            return ""

    def _montar_prompt(
        self,
        input_original: dict[str, Any],
        output: AgentOutput,
        manifest: AgentManifest,
        padrao: str,
        aprendizados: str,
    ) -> str:
        return (
            "Voce e a Stella, supervisora de qualidade de agentes especialistas.\n"
            f"Agente: {manifest.nome} ({manifest.tipo}, setor {manifest.setor})\n\n"
            f"Input original do Bruno:\n{json.dumps(input_original, ensure_ascii=False)}\n\n"
            f"Output do agente:\n{json.dumps(output.resultado, ensure_ascii=False)}\n\n"
            f"Padrao do setor (C04/Padroes/{manifest.setor}.md):\n{padrao or '(nao declarado)'}\n\n"
            f"Aprendizados acumulados:\n{aprendizados or '(nenhum)'}\n\n"
            "Avalie e responda APENAS com um JSON valido no formato:\n"
            '{"veredicto": "aprovado|refazer|aceitar_com_aviso|rejeitar", "feedback": "explicacao em PT-BR"}'
        )

    def _parsear_resposta(self, texto: str) -> tuple[Veredicto, str]:
        try:
            dados = json.loads(texto)
        except (json.JSONDecodeError, ValueError):
            return ("rejeitar", f"Resposta do LLM nao foi JSON valido: {texto[:200]}")

        veredicto_str = dados.get("veredicto", "")
        feedback = str(dados.get("feedback", ""))
        veredictos_validos = get_args(Veredicto)
        if veredicto_str not in veredictos_validos:
            return (
                "rejeitar",
                f"Veredicto invalido '{veredicto_str}' (esperado {veredictos_validos})",
            )
        return (veredicto_str, feedback)
