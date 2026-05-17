"""QualityReviewer — Stella supervisora dos agentes (Q2=E loop).

Esta classe orquestra a revisao de qualidade. Decisoes:
- Q1=C: ReviewPolicy (em policies.py) decide SE revisar.
- Q2=E: combinacao — refaz 1x, depois aceita com aviso (Task 10).
- Q3=C: padroes hibridos — declarados em C04/Padroes/ + Stella aprende (FeedbackLogger em feedback.py).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from stella.framework.agent import AgentOutput
from stella.framework.manifest import AgentManifest
from stella.framework.quality.policies import ReviewPolicy

Veredicto = Literal["aprovado", "refazer", "aceitar_com_aviso", "rejeitar"]


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
    """Aplica revisao de qualidade no output de cada agente.

    FB-M3 Task 8 entrega caminho base (policy diz nao -> aprovado).
    FB-M3 Task 9 adiciona caminho com LLM (Sonnet avalia output).
    FB-M3 Task 10 adiciona loop retry (Q2=E).
    """

    def __init__(
        self,
        llm: object | None,
        vault: object | None,
        skills_reg: object | None,
        policy: ReviewPolicy,
    ) -> None:
        # Tipos object|None aqui por simetria com Agent.__init__ — Task 16
        # estreita estes tipos quando consolidarmos a API publica.
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

        # Caminho com LLM entra em Task 9. Por enquanto: aprova com nota.
        return ReviewResult(
            veredicto="aprovado",
            feedback="caminho LLM pendente (Task 9 do FB-M3)",
            output_final=output,
        )
