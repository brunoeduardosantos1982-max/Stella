"""Testes da extensão de vault_scope para list[str] no AgentManifest."""

from typing import Any

import pytest

from stella.framework.manifest import AgentManifest
from stella.framework.testing.fakes import FakeVault


def _kwargs_minimos() -> dict[str, Any]:
    return dict(
        nome="x",
        tipo="especialista",
        setor="testes",
        descricao="descricao com mais de dez caracteres",
        execucao="in_process",
        modelo_minimo="gemma",
        inputs_obrigatorios=[],
        exemplo_uso={},
        quando_usar="quando_usar com mais de dez caracteres",
    )


def test_vault_scope_aceita_string_unica() -> None:
    """Backward compat: scope como string única continua funcionando, vira lista de 1."""
    m = AgentManifest(
        **_kwargs_minimos(),
        vault_scope="C04 Claude Obsidian/x/**",
    )
    assert m.vault_scope == ["C04 Claude Obsidian/x/**"]


def test_vault_scope_aceita_lista() -> None:
    """Nova capacidade: scope como lista de globs."""
    scopes = [
        "C04 Claude Obsidian/projetos e specs/mktmagneto.ia/**",
        "C04 Claude Obsidian/outputs/mktmagneto-ia/**",
        "C04 Claude Obsidian/Stella-publicacao/fila/**",
    ]
    m = AgentManifest(
        **_kwargs_minimos(),
        vault_scope=scopes,
    )
    assert m.vault_scope == scopes


def test_scoped_aceita_lista_e_or_match() -> None:
    """Scope com 2 globs → permite acesso aos dois, bloqueia paths fora."""
    vault = FakeVault(
        {
            "C04 Claude Obsidian/projetos e specs/mktmagneto.ia/spec.md": ("conteudo spec", {}),
            "C04 Claude Obsidian/outputs/mktmagneto-ia/calendario.md": ("calendario", {}),
            "C04 Claude Obsidian/outra/coisa.md": ("nao deveria ler", {}),
        }
    )
    scopes = [
        "C04 Claude Obsidian/projetos e specs/mktmagneto.ia/**",
        "C04 Claude Obsidian/outputs/mktmagneto-ia/**",
    ]
    scoped = vault.scoped(scopes)

    n1 = scoped.read_note("C04 Claude Obsidian/projetos e specs/mktmagneto.ia/spec.md")
    n2 = scoped.read_note("C04 Claude Obsidian/outputs/mktmagneto-ia/calendario.md")
    assert n1.content == "conteudo spec"
    assert n2.content == "calendario"

    with pytest.raises((PermissionError, FileNotFoundError)):
        scoped.read_note("C04 Claude Obsidian/outra/coisa.md")


def test_scoped_string_unica_continua_funcionando() -> None:
    """Regressão: string única passada para scoped() ainda funciona (backward compat)."""
    vault = FakeVault(
        {
            "a/x.md": ("hi", {}),
            "b/y.md": ("byebye", {}),
        }
    )
    scoped = vault.scoped("a/**")
    assert scoped.read_note("a/x.md").content == "hi"

    with pytest.raises((PermissionError, FileNotFoundError)):
        scoped.read_note("b/y.md")
