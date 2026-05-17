import pytest

from stella.framework.agent import Agent, AgentOutput
from stella.framework.errors import DelegationDepthExceeded
from stella.framework.manifest import AgentManifest


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


def _manifest_para_teste() -> AgentManifest:
    from stella.framework.manifest import CapacidadesExternas

    return AgentManifest(
        nome="t",
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


def test_agent_aceita_manifest_via_kwarg() -> None:
    m = _manifest_para_teste()
    a = _AgenteFake(manifest=m)
    assert a._manifest is m


def test_agent_aceita_todas_as_deps_opcionais_via_kwargs() -> None:
    """Garante que o __init__ aceita todas as 9 dependências como kwargs."""
    m = _manifest_para_teste()
    a = _AgenteFake(
        manifest=m,
        vault=None,
        llm=None,
        skills=[],
        mcps=[],
        rag=None,
        tracker=None,
        logger=None,
        registry=None,
    )
    assert a._manifest is m
    assert a._skills == []
    assert a._mcps == []


def test_agent_sem_args_continua_funcionando_compat_fb_m1() -> None:
    """Construtor sem args ainda funciona — testes do FB-M1 não quebram."""
    a = _AgenteFake()
    assert a._manifest is None
    assert a._registry is None
