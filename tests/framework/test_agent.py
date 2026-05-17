import pytest

from stella.framework.agent import Agent, AgentOutput
from stella.framework.errors import DelegationDepthExceeded


def test_agent_output_minimo() -> None:
    out = AgentOutput(resultado={"texto": "ok"})
    assert out.resultado == {"texto": "ok"}
    assert out.sucesso is True
    assert out.mensagens == []
    assert out.custo_estimado_usd == 0.0


def test_agent_output_com_aviso() -> None:
    out = AgentOutput(
        resultado={"copy": "..."},
        sucesso=True,
        mensagens=["abaixo do padrão de tom"],
        custo_estimado_usd=0.012,
    )
    assert out.sucesso is True
    assert "abaixo do padrão de tom" in out.mensagens
    assert out.custo_estimado_usd == 0.012


def test_agent_output_falha() -> None:
    out = AgentOutput(resultado={}, sucesso=False, mensagens=["timeout"])
    assert out.sucesso is False


class _AgenteFake(Agent):
    """Subclasse mínima de Agent para testar a ABC e o delegate_to."""

    def execute(self, input: dict) -> AgentOutput:
        return AgentOutput(resultado={"echo": input})


def test_agent_e_abstrato() -> None:
    with pytest.raises(TypeError):
        Agent()  # type: ignore[abstract]


def test_agent_subclasse_pode_ser_instanciada() -> None:
    a = _AgenteFake()
    assert a.execute({"x": 1}).resultado == {"echo": {"x": 1}}


def test_delegate_to_sem_registry_levanta_erro() -> None:
    a = _AgenteFake()
    with pytest.raises(RuntimeError, match="registry"):
        a.delegate_to("outro_agente", {"x": 1})


def test_delegate_to_depth_padrao_levanta_quando_passar_de_5() -> None:
    """O depth control DEVE proteger contra loops infinitos."""
    a = _AgenteFake()
    with pytest.raises(DelegationDepthExceeded):
        a.delegate_to("x", {}, _depth=5)


def test_delegate_to_depth_4_ainda_permite() -> None:
    """depth=4 ainda pode tentar (vai falhar por falta de registry, não por depth)."""
    a = _AgenteFake()
    with pytest.raises(RuntimeError, match="registry"):
        a.delegate_to("x", {}, _depth=4)
