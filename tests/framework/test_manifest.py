from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from stella.domain.enums import ModeloIA
from stella.framework.errors import ManifestError
from stella.framework.manifest import AgentManifest, CapacidadesExternas, load_manifest


def test_capacidades_externas_padrao_vazio() -> None:
    c = CapacidadesExternas()
    assert c.skills == []
    assert c.mcps == []
    assert c.optional_mcps == []
    assert c.rag is None


def test_capacidades_externas_com_listas() -> None:
    c = CapacidadesExternas(
        skills=["marketing-copy-pt-br", "ab-testing"],
        mcps=["brave-search"],
        optional_mcps=["perplexity"],
        rag="corpus-copies-anteriores",
    )
    assert "marketing-copy-pt-br" in c.skills
    assert "brave-search" in c.mcps
    assert "perplexity" in c.optional_mcps
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
    assert m.timeout_s == 300.0


def test_manifest_http_exige_endpoint() -> None:
    payload = _manifest_valido_minimo()
    payload["execucao"] = "http"
    with pytest.raises(ValidationError, match="endpoint"):
        AgentManifest(**payload)


def test_manifest_timeout_precisa_ser_positivo() -> None:
    payload = _manifest_valido_minimo()
    payload["timeout_s"] = 0
    with pytest.raises(ValidationError):
        AgentManifest(**payload)


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


_MANIFEST_VALIDO_YAML = """
nome: agente_copy
tipo: especialista
setor: marketing
descricao: Escreve copy de marketing para anúncios e landing pages.
execucao: in_process
modelo_minimo: gemma
inputs_obrigatorios:
  - brief
  - publico_alvo
exemplo_uso:
  brief: "lançamento curso X"
  publico_alvo: "empreendedores"
quando_usar: tarefas envolvendo criar ou revisar texto promocional
capacidades_externas:
  skills: [marketing-copy-pt-br]
  mcps: [brave-search]
vault_scope: "C04 Claude Obsidian/Stella-workspace/marketing/**"
"""


def test_load_manifest_arquivo_valido(tmp_path: Path) -> None:
    p = tmp_path / "manifest.yaml"
    p.write_text(_MANIFEST_VALIDO_YAML, encoding="utf-8")

    m = load_manifest(p)

    assert m.nome == "agente_copy"
    assert "brave-search" in m.capacidades_externas.mcps


def test_load_manifest_yaml_malformado_levanta_manifest_error(tmp_path: Path) -> None:
    p = tmp_path / "manifest.yaml"
    p.write_text("nome: [não fecha colchete", encoding="utf-8")

    with pytest.raises(ManifestError, match="YAML"):
        load_manifest(p)


def test_load_manifest_arquivo_inexistente_levanta_manifest_error(tmp_path: Path) -> None:
    p = tmp_path / "nao-existe.yaml"
    with pytest.raises(ManifestError, match="não encontrado"):
        load_manifest(p)


def test_load_manifest_campo_obrigatorio_faltando_levanta_manifest_error(
    tmp_path: Path,
) -> None:
    p = tmp_path / "manifest.yaml"
    p.write_text(
        "nome: agente_x\ntipo: especialista\nsetor: x\n",
        encoding="utf-8",
    )
    with pytest.raises(ManifestError, match="campo"):
        load_manifest(p)


def _deps_minimas(tmp_path: Path):
    """Helper: monta FrameworkDeps minimos para testar validate_manifest_resources."""
    from stella.adapters.vault.obsidian_vault import ObsidianVaultRepository
    from stella.framework.builder import FrameworkDeps
    from stella.framework.registry import AgentRegistry
    from stella.framework.resources.mcp_registry import MCPRegistry
    from stella.framework.resources.rag_registry import RAGRegistry
    from stella.framework.resources.skills_registry import SkillsRegistry

    skills_dir = tmp_path / "skills"
    skills_dir.mkdir(exist_ok=True)
    vault_root = tmp_path / "vault"
    vault_root.mkdir(exist_ok=True)
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir(exist_ok=True)
    return FrameworkDeps(
        vault=ObsidianVaultRepository(vault_root),
        llm=None,
        skills_reg=SkillsRegistry(skills_dir),
        mcp_reg=MCPRegistry(),
        rag_reg=RAGRegistry(),
        tracker=None,
        logger=None,
        registry=AgentRegistry(agents_dir),
    )


def _manifest_com_caps(**caps: Any) -> AgentManifest:
    return AgentManifest(
        nome="ag",
        tipo="especialista",
        setor="x",
        descricao="agente teste validate",
        execucao="in_process",
        modelo_minimo="gemma",
        inputs_obrigatorios=[],
        exemplo_uso={},
        quando_usar="apenas em testes do validate",
        capacidades_externas=CapacidadesExternas(**caps),
    )


def test_validate_manifest_resources_ok_quando_tudo_existe(tmp_path: Path) -> None:
    from stella.domain.conexao_mcp import ConexaoMCP
    from stella.framework.manifest import validate_manifest_resources

    deps = _deps_minimas(tmp_path)
    skills_dir = tmp_path / "skills"
    (skills_dir / "copy-pt.md").write_text(
        "---\nid: copy-pt\nnome: Copy\ndescricao: skill\ngatilhos: []\nmodelo_minimo: gemma\ntags: []\n---\n",
        encoding="utf-8",
    )
    # Reconstruir skills_reg para pegar o arquivo recém-criado
    from stella.framework.resources.skills_registry import SkillsRegistry

    deps.skills_reg = SkillsRegistry(skills_dir)
    deps.mcp_reg.register(ConexaoMCP(nome="brave", tipo="http", endpoint="http://x"))

    m = _manifest_com_caps(skills=["copy-pt"], mcps=["brave"])
    assert validate_manifest_resources(m, deps) == []


def test_validate_manifest_resources_skill_faltando_devolve_msg(tmp_path: Path) -> None:
    from stella.framework.manifest import validate_manifest_resources

    deps = _deps_minimas(tmp_path)
    m = _manifest_com_caps(skills=["nao-existe"])
    erros = validate_manifest_resources(m, deps)
    assert len(erros) == 1
    assert "nao-existe" in erros[0]
    assert "skill" in erros[0].lower()


def test_validate_manifest_resources_mcp_faltando_devolve_msg(tmp_path: Path) -> None:
    from stella.framework.manifest import validate_manifest_resources

    deps = _deps_minimas(tmp_path)
    m = _manifest_com_caps(mcps=["mcp-x"])
    erros = validate_manifest_resources(m, deps)
    assert len(erros) == 1
    assert "mcp-x" in erros[0]
    assert "mcp" in erros[0].lower()


def test_validate_manifest_resources_optional_mcp_faltando_nao_devolve_msg(
    tmp_path: Path,
) -> None:
    from stella.framework.manifest import validate_manifest_resources

    deps = _deps_minimas(tmp_path)
    m = _manifest_com_caps(optional_mcps=["perplexity"])
    assert validate_manifest_resources(m, deps) == []


def test_validate_manifest_resources_rag_faltando_devolve_msg(tmp_path: Path) -> None:
    from stella.framework.manifest import validate_manifest_resources

    deps = _deps_minimas(tmp_path)
    m = _manifest_com_caps(rag="corpus-x")
    erros = validate_manifest_resources(m, deps)
    assert len(erros) == 1
    assert "corpus-x" in erros[0]
    assert "rag" in erros[0].lower()
