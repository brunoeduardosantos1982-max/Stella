"""Tipos centrais para agentes do Sistema Multi-Agente.

Define o contrato `Agent` (ABC), o `AgentOutput` (dataclass de retorno),
e o helper `delegate_to` que Coordenadores usam para chamar Especialistas.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentOutput:
    """Output canônico que todo agente devolve.

    Atributos:
        resultado: payload principal — estrutura livre, definida por cada agente.
        sucesso: True se a execução cumpriu o objetivo; False se falhou (com
            mensagens explicando).
        mensagens: avisos, observações ou diagnósticos. Usado pela Stella
            para compor a resposta final ao Bruno (ex: "abaixo do padrão").
        custo_estimado_usd: custo da execução em USD (tokens LLM consumidos).
            Stella soma para alimentar o teto mensal de US$100.
    """

    resultado: dict[str, Any]
    sucesso: bool = True
    mensagens: list[str] = field(default_factory=list)
    custo_estimado_usd: float = 0.0
