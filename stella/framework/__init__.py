"""Framework base do Sistema Multi-Agente.

Tipos centrais para construir agentes que rodam dentro da Stella.
Spec: bssurf00/C04 Claude Obsidian/projetos e specs/Sistema Multi-Agente/
      2026-05-16 — Sub-projeto A — Framework Base — Design.md

FB-M1 (✅): tipos base e contratos.
FB-M2 (✅ este milestone): registries, builder, hooks de extensibilidade
    para Sub-projetos E-I.
FB-M3 (próximo): QualityReviewer, fixtures de teste, CLI stella agent new.
"""

from stella.framework.agent import (
    MAX_DELEGATION_DEPTH,
    Agent,
    AgentOutput,
)
from stella.framework.builder import FrameworkDeps, build_agent
from stella.framework.client import (
    AgentClient,
    HttpAgentClient,
    InProcessClient,
)
from stella.framework.errors import (
    AgentExecutionError,
    AgentNotFoundError,
    AgentTimeoutError,
    AgentUnavailableError,
    BudgetExceededError,
    DelegationDepthExceeded,
    FrameworkError,
    ManifestError,
    MCPError,
    MCPNotFoundError,
    QualityReviewFailed,
    RAGNotFoundError,
    RegistryError,
    SkillNotFoundError,
)
from stella.framework.manifest import (
    AgentManifest,
    CapacidadesExternas,
    load_manifest,
)
from stella.framework.quality.feedback import FeedbackLogger
from stella.framework.quality.policies import ReviewPolicy
from stella.framework.quality.reviewer import QualityReviewer, ReviewResult
from stella.framework.registry import AgentRegistry
from stella.framework.resources.mcp_registry import MCPRegistry
from stella.framework.resources.rag_registry import RAGRegistry
from stella.framework.resources.skills_registry import SkillsRegistry
from stella.framework.sandbox import Sandbox
from stella.framework.scheduling import BackgroundScheduler, IdleTask
from stella.framework.skills_editor import SkillEditor

__all__ = [
    "MAX_DELEGATION_DEPTH",
    "Agent",
    "AgentClient",
    "AgentExecutionError",
    "AgentManifest",
    "AgentNotFoundError",
    "AgentOutput",
    "AgentRegistry",
    "AgentTimeoutError",
    "AgentUnavailableError",
    "BackgroundScheduler",
    "BudgetExceededError",
    "CapacidadesExternas",
    "DelegationDepthExceeded",
    "FeedbackLogger",
    "FrameworkDeps",
    "FrameworkError",
    "HttpAgentClient",
    "IdleTask",
    "InProcessClient",
    "MCPError",
    "MCPNotFoundError",
    "MCPRegistry",
    "ManifestError",
    "QualityReviewFailed",
    "QualityReviewer",
    "RAGNotFoundError",
    "RAGRegistry",
    "RegistryError",
    "ReviewPolicy",
    "ReviewResult",
    "Sandbox",
    "SkillEditor",
    "SkillNotFoundError",
    "SkillsRegistry",
    "build_agent",
    "load_manifest",
]
