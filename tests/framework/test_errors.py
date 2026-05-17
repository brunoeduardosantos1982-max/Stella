import pytest

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


def test_framework_error_e_subclasse_de_exception() -> None:
    assert issubclass(FrameworkError, Exception)


def test_manifest_error_subclasse_de_framework() -> None:
    assert issubclass(ManifestError, FrameworkError)


def test_registry_error_subclasse_de_framework() -> None:
    assert issubclass(RegistryError, FrameworkError)


def test_not_found_errors_subclasses_de_registry() -> None:
    assert issubclass(AgentNotFoundError, RegistryError)
    assert issubclass(SkillNotFoundError, RegistryError)
    assert issubclass(MCPNotFoundError, RegistryError)
    assert issubclass(RAGNotFoundError, RegistryError)


def test_agent_runtime_errors_subclasses_de_framework() -> None:
    assert issubclass(AgentExecutionError, FrameworkError)
    assert issubclass(AgentUnavailableError, FrameworkError)
    assert issubclass(AgentTimeoutError, FrameworkError)


def test_delegation_depth_exceeded_subclasse_de_framework() -> None:
    assert issubclass(DelegationDepthExceeded, FrameworkError)


def test_mcp_error_subclasse_de_framework() -> None:
    assert issubclass(MCPError, FrameworkError)


def test_quality_review_failed_subclasse_de_framework() -> None:
    assert issubclass(QualityReviewFailed, FrameworkError)


def test_budget_exceeded_subclasse_de_framework() -> None:
    assert issubclass(BudgetExceededError, FrameworkError)


def test_manifest_error_pode_ser_levantado_com_mensagem() -> None:
    with pytest.raises(ManifestError, match="skill 'X' não existe"):
        raise ManifestError("skill 'X' não existe no registry")
