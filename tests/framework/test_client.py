import pytest

from stella.framework.client import AgentClient


def test_agent_client_e_abstrato() -> None:
    with pytest.raises(TypeError):
        AgentClient()  # type: ignore[abstract]
