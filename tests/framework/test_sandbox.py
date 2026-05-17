import pytest

from stella.framework.agent import Agent, AgentOutput
from stella.framework.sandbox import Sandbox


def test_sandbox_e_abstrato() -> None:
    with pytest.raises(TypeError):
        Sandbox()  # type: ignore[abstract]


def test_sandbox_subclasse_pode_implementar() -> None:
    class _AgenteEcho(Agent):
        def execute(self, input: dict) -> AgentOutput:
            return AgentOutput(resultado={"echo": input})

    class _FakeSandbox(Sandbox):
        def __init__(self) -> None:
            self._estado: dict[str, str] = {}

        def run_isolated(self, agent: Agent, payload: dict) -> AgentOutput:
            self._estado["ultima_chamada"] = str(payload)
            return agent.execute(payload)

        def snapshot_state(self) -> dict:
            return dict(self._estado)

    sb = _FakeSandbox()
    out = sb.run_isolated(_AgenteEcho(), {"x": 1})
    assert out.resultado == {"echo": {"x": 1}}
    assert "ultima_chamada" in sb.snapshot_state()
