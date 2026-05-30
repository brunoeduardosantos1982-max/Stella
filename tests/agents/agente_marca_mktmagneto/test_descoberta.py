"""Testa que o agente_marca_mktmagneto é descoberto pelo AgentRegistry."""

from pathlib import Path

import stella as _stella
from stella.framework.registry import AgentRegistry


def test_agente_marca_descoberto():
    """O agente está em stella/agents/ e o AgentRegistry o encontra."""
    agents_dir = Path(_stella.__file__).parent / "agents"
    reg = AgentRegistry(agents_dir)
    manifests = {m.nome for m in reg.list_manifests()}
    assert "agente_marca_mktmagneto" in manifests


def test_manifest_basico_correto():
    """Validações dos principais campos do manifest."""
    agents_dir = Path(_stella.__file__).parent / "agents"
    reg = AgentRegistry(agents_dir)
    manifest = next(m for m in reg.list_manifests() if m.nome == "agente_marca_mktmagneto")
    assert manifest.tipo == "coordenador"
    assert manifest.setor == "marketing-marca"
    assert manifest.execucao == "in_process"
    assert "tavily" in manifest.capacidades_externas.mcps
    assert "perplexity" in manifest.capacidades_externas.optional_mcps
    # especialistas delgados
    assert "copywriter" in manifest.especialistas
    assert "designer" in manifest.especialistas
    # vault_scope é lista
    assert isinstance(manifest.vault_scope, list)
    assert len(manifest.vault_scope) >= 3
