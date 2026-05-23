"""Testes da extensão de vault_scope para list[str] no AgentManifest."""

from stella.framework.manifest import AgentManifest


def _kwargs_minimos():
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


def test_vault_scope_aceita_string_unica():
    """Backward compat: scope como string única continua funcionando, vira lista de 1."""
    m = AgentManifest(
        **_kwargs_minimos(),
        vault_scope="C04 Claude Obsidian/x/**",
    )
    assert m.vault_scope == ["C04 Claude Obsidian/x/**"]


def test_vault_scope_aceita_lista():
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
