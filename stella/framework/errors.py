"""Hierarquia de erros do framework multi-agente.

Toda exceção do framework herda de FrameworkError. Usecases capturam
apenas os tipos que sabem tratar; não-tratados sobem para a Stella
que decide como comunicar ao Bruno.
"""


class FrameworkError(Exception):
    """Raiz de todos os erros do framework multi-agente."""


# --- Erros de manifest / configuração ---


class ManifestError(FrameworkError):
    """Manifest inválido: YAML malformado, schema errado, referência
    para recurso (skill/MCP/RAG) que não existe no registry."""


# --- Erros de registry / discovery ---


class RegistryError(FrameworkError):
    """Erro genérico de qualquer registry."""


class AgentNotFoundError(RegistryError):
    """Nome de agente solicitado não está registrado."""


class SkillNotFoundError(RegistryError):
    """Nome de skill solicitado não está no SkillsRegistry."""


class MCPNotFoundError(RegistryError):
    """Nome de MCP solicitado não está configurado."""


class RAGNotFoundError(RegistryError):
    """Nome de corpus RAG solicitado não está registrado."""


# --- Erros de execução de agente ---


class AgentExecutionError(FrameworkError):
    """Exceção dentro do `execute()` do agente — encapsulada na fronteira
    para isolar a Stella e o caller do erro bruto do agente."""


class AgentUnavailableError(FrameworkError):
    """Agente HTTP offline (servidor não responde) ou processo in-process
    morto. Stella decide se inicia / tenta de novo / pede confirmação."""


class AgentTimeoutError(FrameworkError):
    """Execução do agente excedeu o timeout configurado."""


# --- Erros de orquestração ---


class DelegationDepthExceeded(FrameworkError):
    """Cadeia de delegate_to excedeu profundidade máxima (default 5) —
    sinal de loop infinito ou design problemático."""


# --- Erros de recursos externos ---


class MCPError(FrameworkError):
    """MCP externo falhou (rede, auth, formato de resposta)."""


# --- Erros de qualidade e orçamento ---


class QualityReviewFailed(FrameworkError):
    """QualityReviewer reprovou output após esgotar tentativas (Q2=E)."""


class BudgetExceededError(FrameworkError):
    """Teto mensal de US$100 atingido — Stella pausa chamadas LLM."""
