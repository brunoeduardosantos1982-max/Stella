"""Framework base do Sistema Multi-Agente.

Tipos centrais para construir agentes que rodam dentro da Stella.
Spec: bssurf00/C04 Claude Obsidian/projetos e specs/Sistema Multi-Agente/
      2026-05-16 — Sub-projeto A — Framework Base — Design.md

FB-M1 (este milestone): tipos base e contratos. FB-M2 adiciona registries
e builder; FB-M3 adiciona QualityReviewer, fixtures de teste e CLI.
"""

from stella.framework.agent import (
    MAX_DELEGATION_DEPTH,
    Agent,
    AgentOutput,
)
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

__all__ = [
    "MAX_DELEGATION_DEPTH",
    "Agent",
    "AgentClient",
    "AgentExecutionError",
    "AgentManifest",
    "AgentNotFoundError",
    "AgentOutput",
    "AgentTimeoutError",
    "AgentUnavailableError",
    "BudgetExceededError",
    "CapacidadesExternas",
    "DelegationDepthExceeded",
    "FrameworkError",
    "HttpAgentClient",
    "InProcessClient",
    "MCPError",
    "MCPNotFoundError",
    "ManifestError",
    "QualityReviewFailed",
    "RAGNotFoundError",
    "RegistryError",
    "SkillNotFoundError",
    "load_manifest",
]
