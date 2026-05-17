from pathlib import Path

from stella.framework.testing.deps import make_fake_deps


def test_make_fake_deps_devolve_framework_deps_completo(tmp_path: Path) -> None:
    deps = make_fake_deps(agents_dir=tmp_path)
    assert deps.vault is not None
    assert deps.llm is not None
    assert deps.skills_reg is not None
    assert deps.mcp_reg is not None
    assert deps.rag_reg is not None
    assert deps.tracker is not None
    assert deps.logger is not None
    assert deps.registry is not None


def test_make_fake_deps_aceita_llm_responses(tmp_path: Path) -> None:
    deps = make_fake_deps(agents_dir=tmp_path, llm_responses=["a", "b"])
    provider = deps.llm.select()  # type: ignore[union-attr]
    assert provider.complete("p1").texto == "a"
    assert provider.complete("p2").texto == "b"


def test_make_fake_deps_aceita_vault_notes(tmp_path: Path) -> None:
    deps = make_fake_deps(
        agents_dir=tmp_path,
        vault_notes={
            "A00 Inbox/oi.md": ("ola", {"tipo": "ideia"}),
        },
    )
    assert deps.vault.note_exists("A00 Inbox/oi.md") is True


def test_make_fake_deps_aceita_mcps_pre_registradas(tmp_path: Path) -> None:
    from stella.domain.conexao_mcp import ConexaoMCP

    mcp = ConexaoMCP(nome="brave", tipo="http", endpoint="http://x", category="research")
    deps = make_fake_deps(agents_dir=tmp_path, mcps=[mcp])
    assert deps.mcp_reg.get("brave").nome == "brave"
