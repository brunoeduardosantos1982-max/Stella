"""Agente _smoke_ — chama LLM uma vez e devolve eco do texto recebido."""

from __future__ import annotations

from typing import Any

from stella.framework.agent import Agent as BaseAgent
from stella.framework.agent import AgentOutput


class Agent(BaseAgent):
    """Agente smoke setor=testes. NAO passa por QualityReviewer."""

    def execute(self, input: dict[str, Any]) -> AgentOutput:
        texto = str(input.get("texto", "ping"))

        if self._llm is None:
            return AgentOutput(
                resultado={"echo": texto, "llm_chamado": False},
                sucesso=True,
                mensagens=["LLM nao configurado — eco direto sem chamar provider"],
            )

        provider = self._llm.select(complexity="low")
        resposta = provider.complete(f"Responda apenas com: '{texto}'")
        return AgentOutput(
            resultado={"echo": resposta.texto, "llm_chamado": True},
            sucesso=True,
        )
