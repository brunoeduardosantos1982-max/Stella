"""make_fake_deps — helper que monta FrameworkDeps com Fakes para testes.

Uso tipico em test de agente:

    def test_meu_agente(tmp_path):
        deps = make_fake_deps(
            agents_dir=tmp_path,
            llm_responses=["resposta do LLM"],
            vault_notes={"A00 Inbox/x.md": ("conteudo", {"tipo": "ideia"})},
        )
        agent = build_agent(manifest, deps)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from stella.adapters.llm.router import LLMRouter
from stella.domain.conexao_mcp import ConexaoMCP
from stella.framework.builder import FrameworkDeps
from stella.framework.registry import AgentRegistry
from stella.framework.resources.mcp_registry import MCPRegistry
from stella.framework.resources.rag_registry import RAGRegistry
from stella.framework.resources.skills_registry import SkillsRegistry
from stella.framework.testing.fakes import FakeLLM, FakeLogger, FakeTracker, FakeVault


def make_fake_deps(
    agents_dir: Path,
    *,
    llm_responses: list[str] | None = None,
    vault_notes: dict[str, tuple[str, dict[str, Any]]] | None = None,
    mcps: list[ConexaoMCP] | None = None,
    skills_dir: Path | None = None,
) -> FrameworkDeps:
    """Constroi FrameworkDeps populado com Fakes — pronto para testes.

    Args:
        agents_dir: pasta usada pelo AgentRegistry (pode estar vazia).
        llm_responses: respostas pre-determinadas do FakeLLM.
        vault_notes: notas iniciais no FakeVault.
        mcps: ConexaoMCPs pre-registradas no MCPRegistry.
        skills_dir: pasta de skills (default: pasta vazia em agents_dir.parent).
    """
    fake_llm = FakeLLM(responses=llm_responses)
    router = LLMRouter(gemma=fake_llm, anthropic=fake_llm, default="gemma")

    mcp_reg = MCPRegistry()
    for m in mcps or []:
        mcp_reg.register(m)

    skills_dir = skills_dir if skills_dir is not None else agents_dir.parent / "skills_vazio"
    skills_dir.mkdir(parents=True, exist_ok=True)

    return FrameworkDeps(
        vault=FakeVault(notes=vault_notes),
        llm=router,
        skills_reg=SkillsRegistry(skills_dir),
        mcp_reg=mcp_reg,
        rag_reg=RAGRegistry(),
        tracker=FakeTracker(),
        logger=FakeLogger(),
        registry=AgentRegistry(agents_dir),
    )
