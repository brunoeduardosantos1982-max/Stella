"""Garante que os símbolos públicos do framework podem ser importados
direto de `stella.framework` sem precisar conhecer o módulo interno."""


def test_pode_importar_tipos_centrais_de_framework_root() -> None:
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
