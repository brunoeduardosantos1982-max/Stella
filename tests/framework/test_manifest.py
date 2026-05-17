from typing import Any

import pytest
from pydantic import ValidationError

from stella.domain.enums import ModeloIA
from stella.framework.manifest import AgentManifest, CapacidadesExternas


def test_capacidades_externas_padrao_vazio() -> None:
    c = CapacidadesExternas()
    assert c.skills == []
    assert c.mcps == []
    assert c.rag is None


def test_capacidades_externas_com_listas() -> None:
    c = CapacidadesExternas(
        skills=["marketing-copy-pt-br", "ab-testing"],
        mcps=["brave-search"],
        rag="corpus-copies-anteriores",
    )
    assert "marketing-copy-pt-br" in c.skills
    assert "brave-search" in c.mcps
    assert c.rag == "corpus-copies-anteriores"


def _manifest_valido_minimo() -> dict[str, Any]:
    """Payload válido mínimo para construir um AgentManifest."""
    return {
        "nome": "agente_copy",
        "tipo": "especialista",
        "setor": "marketing",
        "descricao": "Escreve copy de marketing.",
        "execucao": "in_process",
        "modelo_minimo": "gemma",
        "inputs_obrigatorios": ["brief", "publico_alvo"],
        "exemplo_uso": {"brief": "lançamento curso X", "publico_alvo": "empreendedores"},
        "quando_usar": "tarefas envolvendo texto promocional",
        "capacidades_externas": {},
        "vault_scope": "C04 Claude Obsidian/Stella-workspace/marketing/**",
    }


def test_manifest_valido_minimo() -> None:
    m = AgentManifest(**_manifest_valido_minimo())
    assert m.nome == "agente_copy"
    assert m.tipo == "especialista"
    assert m.setor == "marketing"
    assert m.modelo_minimo == ModeloIA.GEMMA
    assert m.especialistas == []
    assert m.endpoint is None


def test_manifest_coordenador_pode_listar_especialistas() -> None:
    payload = _manifest_valido_minimo()
    payload["nome"] = "coord_marketing"
    payload["tipo"] = "coordenador"
    payload["especialistas"] = ["agente_copy", "agente_ads", "agente_seo"]
    m = AgentManifest(**payload)
    assert m.tipo == "coordenador"
    assert "agente_copy" in m.especialistas


def test_manifest_http_pode_ter_endpoint() -> None:
    payload = _manifest_valido_minimo()
    payload["execucao"] = "http"
    payload["endpoint"] = "http://localhost:8000"
    m = AgentManifest(**payload)
    assert m.execucao == "http"
    assert m.endpoint == "http://localhost:8000"


def test_manifest_tipo_invalido_levanta_validation_error() -> None:
    payload = _manifest_valido_minimo()
    payload["tipo"] = "robô"
    with pytest.raises(ValidationError):
        AgentManifest(**payload)


def test_manifest_modelo_minimo_invalido_levanta_validation_error() -> None:
    payload = _manifest_valido_minimo()
    payload["modelo_minimo"] = "gpt5"
    with pytest.raises(ValidationError):
        AgentManifest(**payload)


def test_manifest_sem_descricao_levanta_validation_error() -> None:
    payload = _manifest_valido_minimo()
    del payload["descricao"]
    with pytest.raises(ValidationError):
        AgentManifest(**payload)
