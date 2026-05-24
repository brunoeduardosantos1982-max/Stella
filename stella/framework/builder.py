"""FrameworkDeps + build_agent — fabrica agentes com DI a partir do manifest.

build_agent resolve recursos via registries (skills/mcps/rag) e importa a
classe Agent do modulo stella.agents.<nome> (convencao: o __init__.py do
agente expoe `Agent` apontando para a classe concreta).

FB-M3 fechou as limitacoes que FB-M2 tinha (vault.scoped, llm.with_minimum).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from importlib import import_module

from stella.adapters.llm.router import LLMRouter
from stella.adapters.vault.base import VaultRepository
from stella.framework.agent import Agent
from stella.framework.manifest import AgentManifest
from stella.framework.registry import AgentRegistry
from stella.framework.resources.mcp_registry import MCPRegistry
from stella.framework.resources.rag_registry import RAGRegistry
from stella.framework.resources.skills_registry import SkillsRegistry
from stella.framework.tracking import TrackerProtocol


@dataclass
class FrameworkDeps:
    """Dependencias globais do framework. Construidas uma vez na startup.

    `registry` e referencia (nao o objeto final) — bind_builder e chamado
    APOS construir as deps para evitar ciclo Registry -> Builder -> Registry.
    """

    vault: VaultRepository
    llm: LLMRouter | None
    skills_reg: SkillsRegistry
    mcp_reg: MCPRegistry
    rag_reg: RAGRegistry
    tracker: TrackerProtocol | None
    logger: logging.Logger | None
    registry: AgentRegistry


def build_agent(manifest: AgentManifest, deps: FrameworkDeps) -> Agent:
    """Constroi um agente in-process a partir do manifest e das deps globais.

    Passos:
    1. Resolve skills declaradas via SkillsRegistry (erra se faltar).
    2. Resolve MCPs declaradas via MCPRegistry (erra se faltar).
    3. Resolve RAG (se declarado) via RAGRegistry (erra se faltar).
    4. Importa stella.agents.<manifest.nome>.Agent via importlib.
    5. Instancia com todas as deps injetadas via kwargs.

    Raises:
        SkillNotFoundError | MCPNotFoundError | RAGNotFoundError: capacidade
            declarada no manifest nao esta registrada.
        ImportError: pasta stella/agents/<nome>/ nao existe ou nao exporta
            a classe Agent no __init__.py.
        AttributeError: __init__.py do agente nao expoe atributo `Agent`.
    """
    _log = deps.logger or logging.getLogger("stella.framework.builder")
    cap = manifest.capacidades_externas
    skills = [deps.skills_reg.get(sid) for sid in cap.skills]
    mcps = []
    for nome in cap.mcps:
        try:
            mcps.append(deps.mcp_reg.get(nome))
        except Exception:  # noqa: BLE001 — MCP não registrada é opcional (sem chave)
            _log.warning("Agente %s: MCP '%s' nao registrada — ignorada", manifest.nome, nome)
    rag = deps.rag_reg.get(cap.rag) if cap.rag else None

    modulo = import_module(f"stella.agents.{manifest.nome}")
    cls: type[Agent] = modulo.Agent

    vault_scoped = deps.vault.scoped(manifest.vault_scope)
    llm_scoped: LLMRouter | None = None
    if deps.llm is not None:
        llm_scoped = deps.llm.with_minimum(manifest.modelo_minimo)
    return cls(
        manifest=manifest,
        vault=vault_scoped,
        llm=llm_scoped,
        skills=list(skills),
        mcps=list(mcps),
        rag=rag,
        tracker=deps.tracker,
        logger=deps.logger,
        registry=deps.registry,
    )
