"""Garante que os símbolos públicos do framework podem ser importados
direto de `stella.framework` sem precisar conhecer o módulo interno."""


def test_pode_importar_tipos_centrais_fb_m1_de_framework_root() -> None:
    from stella.framework import (
        Agent,
        AgentClient,
        AgentManifest,
        AgentOutput,
        CapacidadesExternas,
        FrameworkError,
        HttpAgentClient,
        InProcessClient,
        load_manifest,
    )

    assert Agent is not None
    assert AgentClient is not None
    assert AgentManifest is not None
    assert AgentOutput is not None
    assert CapacidadesExternas is not None
    assert FrameworkError is not None
    assert HttpAgentClient is not None
    assert InProcessClient is not None
    assert load_manifest is not None


def test_pode_importar_tipos_fb_m2_de_framework_root() -> None:
    """Novos symbols do FB-M2: registries, builder, scheduling, editor, sandbox."""
    from stella.framework import (
        AgentRegistry,
        BackgroundScheduler,
        FrameworkDeps,
        IdleTask,
        MCPRegistry,
        RAGRegistry,
        Sandbox,
        SkillEditor,
        SkillsRegistry,
        build_agent,
    )

    assert AgentRegistry is not None
    assert BackgroundScheduler is not None
    assert FrameworkDeps is not None
    assert IdleTask is not None
    assert MCPRegistry is not None
    assert RAGRegistry is not None
    assert Sandbox is not None
    assert SkillEditor is not None
    assert SkillsRegistry is not None
    assert build_agent is not None
