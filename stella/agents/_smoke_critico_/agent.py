"""Agente _smoke_critico_ — mesma logica de _smoke_ mas setor=copy."""

from __future__ import annotations

from typing import Any

from stella.framework.agent import Agent as BaseAgent
from stella.framework.agent import AgentOutput


class Agent(BaseAgent):
    """Agente smoke setor=copy. PASSA por QualityReviewer."""

    def execute(self, input: dict[str, Any]) -> AgentOutput:
        texto = str(input.get("texto", "ping"))

        if self._llm is None:
            return AgentOutput(
                resultado={"copy": texto, "llm_chamado": False},
                sucesso=True,
            )

        provider = self._llm.select(complexity="low")
        resposta = provider.complete(f"Escreva uma frase curta sobre: {texto}")
        return AgentOutput(
            resultado={"copy": resposta.texto, "llm_chamado": True},
            sucesso=True,
        )
