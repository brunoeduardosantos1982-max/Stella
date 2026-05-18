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


def test_delegate_to_cross_agent_loop_detectado_via_contextvar() -> None:
    """A → B → A → B → ... : ContextVar acumula depth entre agentes diferentes.

    Cada agente reseta seu _depth local mas a ContextVar lembra. Após
    MAX_DELEGATION_DEPTH (=5) níveis na cadeia, levanta DelegationDepthExceeded.
    """
    from stella.framework.client import InProcessClient
    from stella.framework.manifest import CapacidadesExternas

    def _mk_manifest(nome: str) -> AgentManifest:
        return AgentManifest(
            nome=nome,
            tipo="especialista",
            setor="testes",
            descricao=f"agente {nome} para teste de loop cross-agent",
            execucao="in_process",
            modelo_minimo="gemma",
            inputs_obrigatorios=[],
            exemplo_uso={},
            quando_usar="apenas para teste de contextvar loop",
            capacidades_externas=CapacidadesExternas(),
        )

    contador = {"chamadas": 0}

    class _RegistryFake:
        def __init__(self, agentes: dict):
            self._agentes = agentes

        def get(self, nome: str):
            return InProcessClient(agent=self._agentes[nome], manifest=_mk_manifest(nome))

    class _AgentePingPong(Agent):
        """Sempre delega para o oponente (loop forcado)."""

        def __init__(self, *, oponente: str, **kwargs):
            super().__init__(**kwargs)
            self._oponente = oponente

        def execute(self, input: dict) -> AgentOutput:
            contador["chamadas"] += 1
            return self.delegate_to(self._oponente, input)

    agente_a = _AgentePingPong(oponente="b")
    agente_b = _AgentePingPong(oponente="a")
    registry = _RegistryFake({"a": agente_a, "b": agente_b})
    agente_a._registry = registry
    agente_b._registry = registry

    # InProcessClient envolve a exception original em AgentExecutionError
    # quando o agente delegado falha. Capturamos a cadeia inteira.
    from stella.framework.errors import AgentExecutionError

    with pytest.raises((DelegationDepthExceeded, AgentExecutionError)) as exc_info:
        agente_a.execute({"x": 1})
    # Verifica que a causa-raiz é DelegationDepthExceeded
    erro: BaseException | None = exc_info.value
    encontrado = False
    while erro is not None:
        if isinstance(erro, DelegationDepthExceeded):
            encontrado = True
            break
        erro = erro.__cause__
    assert encontrado, "DelegationDepthExceeded deve estar na cadeia de causas"
    assert contador["chamadas"] >= 5


def test_delegate_to_com_registry_chama_execute_do_agente_alvo() -> None:
    """delegate_to resolve agent_name via registry e chama execute()."""
    from stella.framework.client import InProcessClient
    from stella.framework.manifest import CapacidadesExternas

    m_alvo = AgentManifest(
        nome="alvo",
        tipo="especialista",
        setor="testes",
        descricao="agente alvo da delegacao",
        execucao="in_process",
        modelo_minimo="gemma",
        inputs_obrigatorios=[],
        exemplo_uso={},
        quando_usar="testes do delegate_to real",
        capacidades_externas=CapacidadesExternas(),
    )

    class _RegistryFake:
        def get(self, nome: str):
            assert nome == "alvo"
            return InProcessClient(agent=_AgenteFake(), manifest=m_alvo)

    a = _AgenteFake(registry=_RegistryFake())
    out = a.delegate_to("alvo", {"x": 1})
    assert out.resultado == {"echo": {"x": 1}}


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
