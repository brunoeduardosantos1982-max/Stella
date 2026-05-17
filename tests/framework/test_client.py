import pytest

from stella.framework.agent import Agent, AgentOutput
from stella.framework.client import AgentClient, InProcessClient
from stella.framework.errors import AgentExecutionError
from stella.framework.manifest import AgentManifest, CapacidadesExternas


def test_agent_client_e_abstrato() -> None:
    with pytest.raises(TypeError):
        AgentClient()  # type: ignore[abstract]


def _manifest_dummy() -> AgentManifest:
    return AgentManifest(
        nome="dummy",
        tipo="especialista",
        setor="testes",
        descricao="agente para testes do framework",
        execucao="in_process",
        modelo_minimo="gemma",
        inputs_obrigatorios=[],
        exemplo_uso={},
        quando_usar="apenas em testes — não use em produção",
        capacidades_externas=CapacidadesExternas(),
    )


class _AgenteEcho(Agent):
    """Devolve o que recebe — usado para validar o pipeline do client."""

    def execute(self, input: dict) -> AgentOutput:
        return AgentOutput(resultado={"echo": input})


class _AgenteQueExplode(Agent):
    """Sempre levanta exceção — para testar isolamento do client."""

    def execute(self, input: dict) -> AgentOutput:
        raise ZeroDivisionError("falha de propósito")


def test_inprocess_client_chama_execute_do_agente() -> None:
    c = InProcessClient(agent=_AgenteEcho(), manifest=_manifest_dummy())
    out = c.execute({"x": 1})
    assert out.resultado == {"echo": {"x": 1}}


def test_inprocess_client_devolve_manifest() -> None:
    m = _manifest_dummy()
    c = InProcessClient(agent=_AgenteEcho(), manifest=m)
    assert c.manifest() is m


def test_inprocess_client_encapsula_exception_em_agent_execution_error() -> None:
    c = InProcessClient(agent=_AgenteQueExplode(), manifest=_manifest_dummy())
    with pytest.raises(AgentExecutionError, match="falha de propósito"):
        c.execute({})
