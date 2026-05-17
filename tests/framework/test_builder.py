from pathlib import Path

import pytest

from stella.adapters.vault.obsidian_vault import ObsidianVaultRepository
from stella.domain.conexao_mcp import ConexaoMCP
from stella.framework.agent import Agent, AgentOutput
from stella.framework.builder import FrameworkDeps, build_agent
from stella.framework.errors import MCPNotFoundError, SkillNotFoundError
from stella.framework.manifest import AgentManifest, CapacidadesExternas
from stella.framework.registry import AgentRegistry
from stella.framework.resources.mcp_registry import MCPRegistry
from stella.framework.resources.rag_registry import RAGRegistry
from stella.framework.resources.skills_registry import SkillsRegistry


def _deps_para_teste(
    tmp_path: Path,
    skills_dir: Path | None = None,
) -> FrameworkDeps:
    """Helper — monta deps minimas para testar o builder."""
    skills_dir = skills_dir if skills_dir is not None else tmp_path / "skills_vazio"
    skills_dir.mkdir(exist_ok=True)
    agents_dir = tmp_path / "agents"
    agents_dir.mkdir(exist_ok=True)
    vault_root = tmp_path / "vault"
    vault_root.mkdir(exist_ok=True)
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


def _manifest(
    nome: str,
    skills: list[str] | None = None,
    mcps: list[str] | None = None,
) -> AgentManifest:
    return AgentManifest(
        nome=nome,
        tipo="especialista",
        setor="testes",
        descricao="agente de teste do builder",
        execucao="in_process",
        modelo_minimo="gemma",
        inputs_obrigatorios=[],
        exemplo_uso={},
        quando_usar="apenas em testes do builder",
        capacidades_externas=CapacidadesExternas(
            skills=skills or [],
            mcps=mcps or [],
            rag=None,
        ),
    )


class _AgenteEcho(Agent):
    def execute(self, input: dict) -> AgentOutput:
        return AgentOutput(resultado={"echo": input})


def _instalar_agente_no_modulo(monkeypatch: pytest.MonkeyPatch, nome: str) -> None:
    """Registra um modulo fake stella.agents.<nome> com classe Agent = _AgenteEcho."""
    import sys
    import types

    modulo = types.ModuleType(f"stella.agents.{nome}")
    modulo.Agent = _AgenteEcho  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, f"stella.agents.{nome}", modulo)


def test_build_agent_instancia_classe_do_modulo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _instalar_agente_no_modulo(monkeypatch, "agente_x")
    deps = _deps_para_teste(tmp_path)
    agent = build_agent(_manifest("agente_x"), deps)
    assert isinstance(agent, _AgenteEcho)


def test_build_agent_injeta_manifest(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _instalar_agente_no_modulo(monkeypatch, "agente_x")
    deps = _deps_para_teste(tmp_path)
    m = _manifest("agente_x")
    agent = build_agent(m, deps)
    assert agent._manifest is m


def test_build_agent_resolve_skills_e_injeta(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()
    (skills_dir / "copy-pt-br.md").write_text(
        "---\nid: copy-pt-br\nnome: Copy PT\ndescricao: skill x\ngatilhos: []\nmodelo_minimo: gemma\ntags: []\n---\n",
        encoding="utf-8",
    )
    _instalar_agente_no_modulo(monkeypatch, "agente_x")
    deps = _deps_para_teste(tmp_path, skills_dir=skills_dir)

    m = _manifest("agente_x", skills=["copy-pt-br"])
    agent = build_agent(m, deps)
    assert len(agent._skills) == 1
    assert agent._skills[0].id == "copy-pt-br"


def test_build_agent_skill_declarada_mas_nao_registrada_levanta(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _instalar_agente_no_modulo(monkeypatch, "agente_x")
    deps = _deps_para_teste(tmp_path)
    m = _manifest("agente_x", skills=["nao-existe"])
    with pytest.raises(SkillNotFoundError, match="nao-existe"):
        build_agent(m, deps)


def test_build_agent_resolve_mcps_e_injeta(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _instalar_agente_no_modulo(monkeypatch, "agente_x")
    deps = _deps_para_teste(tmp_path)
    deps.mcp_reg.register(ConexaoMCP(nome="brave-search", tipo="http", endpoint="http://x"))
    m = _manifest("agente_x", mcps=["brave-search"])
    agent = build_agent(m, deps)
    assert len(agent._mcps) == 1


def test_build_agent_mcp_declarada_mas_nao_registrada_levanta(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _instalar_agente_no_modulo(monkeypatch, "agente_x")
    deps = _deps_para_teste(tmp_path)
    m = _manifest("agente_x", mcps=["sem-mcp"])
    with pytest.raises(MCPNotFoundError, match="sem-mcp"):
        build_agent(m, deps)


def test_build_agent_modulo_inexistente_levanta_import_error(
    tmp_path: Path,
) -> None:
    deps = _deps_para_teste(tmp_path)
    m = _manifest("modulo_que_nao_existe_no_python")
    with pytest.raises(ImportError):
        build_agent(m, deps)
