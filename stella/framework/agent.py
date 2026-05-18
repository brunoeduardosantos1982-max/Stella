"""Tipos centrais para agentes do Sistema Multi-Agente.

Define o contrato `Agent` (ABC), o `AgentOutput` (dataclass de retorno),
e o helper `delegate_to` que Coordenadores usam para chamar Especialistas.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Any

from stella.adapters.llm.router import LLMRouter
from stella.adapters.vault.base import VaultRepository
from stella.domain.conexao_mcp import ConexaoMCP
from stella.domain.skill import Skill
from stella.framework.errors import DelegationDepthExceeded
from stella.framework.manifest import AgentManifest
from stella.framework.rag import RAGClient
from stella.framework.tracking import TrackerProtocol

# Profundidade máxima de cadeias de delegação (A → B → C → ...).
# Acima disso, suspeita-se de loop infinito; framework cancela.
MAX_DELEGATION_DEPTH = 5

# ContextVar global de framework — acumula depth entre agentes diferentes
# para detectar loops cross-agent (A→B→A→B...). FB-M4 I4.
_delegation_depth_var: ContextVar[int] = ContextVar("stella.framework.delegation_depth", default=0)


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
        llm: LLMRouter | None = None,
        skills: list[Skill] | None = None,
        mcps: list[ConexaoMCP] | None = None,
        rag: RAGClient | None = None,
        tracker: TrackerProtocol | None = None,
        logger: logging.Logger | None = None,
        registry: object | None = None,
    ) -> None:
        """Construtor com Dependency Injection (FB-M2 + FB-M3).

        Todas as deps são opcionais para que subclasses possam ser instanciadas
        sem args em testes unitários ainda sem fixtures.
        Em produção, `build_agent()` injeta tudo a partir do manifest.

        FB-M3 estreitou tipos concretos para llm/skills/mcps/logger.
        `rag`/`tracker`/`registry` permanecem `object | None`: rag stub,
        tracker tem APIs diferentes em testes, registry causaria ciclo
        Registry-Agent-Builder.
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
        _depth: int | None = None,
    ) -> AgentOutput:
        """Coordenadores usam para chamar Especialistas via Registry.

        Args:
            agent_name: nome do agente alvo (deve estar no Registry).
            payload: dict passado para o `execute()` do agente alvo.
            _depth: profundidade atual da cadeia. Se None (default), usa
                `_delegation_depth_var` (ContextVar) que acumula entre agentes
                diferentes — detecta loop cross-agent (A→B→A→B...). Se passado
                explicitamente, sobrescreve a ContextVar (compat com testes
                FB-M1 e uso avançado).

        Raises:
            DelegationDepthExceeded: cadeia atingiu MAX_DELEGATION_DEPTH (5).
            RuntimeError: registry não foi injetado.
            AgentNotFoundError: agent_name não está no registry.
        """
        current = _depth if _depth is not None else _delegation_depth_var.get()

        if current >= MAX_DELEGATION_DEPTH:
            raise DelegationDepthExceeded(
                f"Cadeia de delegação excedeu profundidade {MAX_DELEGATION_DEPTH} "
                f"ao tentar chamar '{agent_name}' (depth={current}). "
                "Suspeita de loop infinito — cancelando."
            )

        if self._registry is None:
            raise RuntimeError(
                "Agent sem registry injetado — não pode delegar. "
                "FB-M2 implementa a injeção via build_agent()."
            )

        token = _delegation_depth_var.set(current + 1)
        try:
            cliente = self._registry.get(agent_name)  # type: ignore[attr-defined]
            return cliente.execute(payload)  # type: ignore[no-any-return]
        finally:
            _delegation_depth_var.reset(token)
