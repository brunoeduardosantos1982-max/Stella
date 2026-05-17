"""Tipos centrais para agentes do Sistema Multi-Agente.

Define o contrato `Agent` (ABC), o `AgentOutput` (dataclass de retorno),
e o helper `delegate_to` que Coordenadores usam para chamar Especialistas.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from stella.adapters.vault.base import VaultRepository
from stella.framework.errors import DelegationDepthExceeded
from stella.framework.manifest import AgentManifest

# Profundidade máxima de cadeias de delegação (A → B → C → ...).
# Acima disso, suspeita-se de loop infinito; framework cancela.
MAX_DELEGATION_DEPTH = 5


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


class Agent(ABC):
    """Classe base de TODOS os agentes (Coordenadores e Especialistas).

    Dependências são injetadas pelo framework no construtor (ver
    `framework.builder.build_agent`). FB-M1 define a interface; FB-M2
    implementa o builder que monta as dependências a partir do manifest.

    Subclasses concretas (Coordenadores e Especialistas) implementam
    apenas `execute(input)`. Coordenadores adicionalmente usam o helper
    `delegate_to(...)` herdado para invocar outros agentes via Registry.

    Atributos esperados pelas subclasses (todos injetados em FB-M2):
        manifest: AgentManifest descrevendo este agente
        vault: VaultClient com scope aplicado (limita acesso)
        llm: LLMRouter (com modelo_minimo do manifest)
        skills: list[Skill] declaradas no manifest
        mcps: list[MCPConnection] declaradas no manifest
        rag: RAGClient | None (se manifest declarar)
        tracker: UsageTracker compartilhado
        logger: Logger estruturado
        registry: AgentRegistry (para Coordenadores fazerem delegate_to)
    """

    def __init__(
        self,
        *,
        manifest: AgentManifest | None = None,
        vault: VaultRepository | None = None,
        llm: object | None = None,
        skills: list[object] | None = None,
        mcps: list[object] | None = None,
        rag: object | None = None,
        tracker: object | None = None,
        logger: object | None = None,
        registry: object | None = None,
    ) -> None:
        """Construtor com Dependency Injection (FB-M2).

        Todas as deps são opcionais para que subclasses possam ser instanciadas
        sem args em testes unitários ainda sem fixtures (FB-M3 traz as Fakes).
        Em produção, `build_agent()` injeta tudo a partir do manifest.

        Tipos `object | None` em `llm`/`skills`/`mcps`/`rag`/`tracker`/`logger`:
        são placeholders. FB-M3 substitui pelos tipos concretos quando os
        adapters reais (LLMRouter, Skill, MCPConnection, etc) consolidarem
        suas APIs públicas. Manter `object` evita imports circulares e não
        empurra escopo de FB-M3 para FB-M2.
        """
        self._manifest = manifest
        self._vault = vault
        self._llm = llm
        self._skills = skills if skills is not None else []
        self._mcps = mcps if mcps is not None else []
        self._rag = rag
        self._tracker = tracker
        self._logger = logger
        self._registry = registry

    @abstractmethod
    def execute(self, input: dict[str, Any]) -> AgentOutput:
        """Executa a tarefa principal do agente. Sobrescrever em subclasse."""
        ...

    def delegate_to(
        self,
        agent_name: str,
        payload: dict[str, Any],
        _depth: int = 0,
    ) -> AgentOutput:
        """Coordenadores usam para chamar Especialistas via Registry.

        Args:
            agent_name: nome do agente alvo (deve estar no Registry).
            payload: dict passado para o `execute()` do agente alvo.
            _depth: profundidade atual da cadeia de delegação. Incrementado
                automaticamente. Levanta `DelegationDepthExceeded` se atingir
                `MAX_DELEGATION_DEPTH` (proteção contra loops).

        Raises:
            DelegationDepthExceeded: cadeia de delegação muito profunda.
            RuntimeError: registry não foi injetado (FB-M2 implementa).
            AgentNotFoundError: agent_name não está no registry.
        """
        if _depth >= MAX_DELEGATION_DEPTH:
            raise DelegationDepthExceeded(
                f"Cadeia de delegação excedeu profundidade {MAX_DELEGATION_DEPTH} "
                f"ao tentar chamar '{agent_name}' (depth={_depth}). "
                "Suspeita de loop infinito — cancelando."
            )

        if self._registry is None:
            raise RuntimeError(
                "Agent sem registry injetado — não pode delegar. "
                "FB-M2 implementa a injeção via build_agent()."
            )

        # FB-M2 vai chamar self._registry.get(agent_name).execute(payload, _depth=_depth+1)
        # Por enquanto, o caminho com registry presente fica para FB-M2.
        raise RuntimeError("delegate_to com registry — implementação em FB-M2")
