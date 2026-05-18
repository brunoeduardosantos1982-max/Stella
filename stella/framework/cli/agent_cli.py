"""Sub-app Typer 'stella agent' — comandos list/show/new.

Cada comando recebe --agents-dir opcional para apontar para uma pasta de
agentes diferente da default (stella/agents). Util para testes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from stella.framework.registry import AgentRegistry

agent_app = typer.Typer(help="Gerencia agentes do Sistema Multi-Agente.")


@agent_app.callback()
def _agent_callback() -> None:
    """Forca Typer a tratar agent_app como multi-comando (mesmo quando ha 1 so)."""


_DEFAULT_AGENTS_DIR = Path(__file__).resolve().parent.parent.parent / "agents"
_DEFAULT_SKILLS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts" / "skills"

_SkillsDirOpt = Annotated[
    Path,
    typer.Option(
        "--skills-dir",
        help="Pasta de skills (usado com --resolve). Default: stella/prompts/skills.",
    ),
]

_AgentsDirOpt = Annotated[
    Path,
    typer.Option(
        "--agents-dir",
        help="Pasta com subpastas de agentes (default: stella/agents).",
    ),
]


@agent_app.command("list")
def list_agents(agents_dir: _AgentsDirOpt = _DEFAULT_AGENTS_DIR) -> None:
    """Lista agentes descobertos no agents_dir."""
    registry = AgentRegistry(agents_dir)
    manifests = registry.list_manifests()
    if not manifests:
        typer.echo(f"Nenhum agente encontrado em {agents_dir} (pasta vazia ou inexistente).")
        raise typer.Exit(code=0)

    for m in manifests:
        typer.echo(f"  {m.nome:35} {m.tipo:12} setor={m.setor:15} ({m.execucao})")


@agent_app.command("show")
def show_agent(
    nome: Annotated[str, typer.Argument(help="Nome do agente")],
    agents_dir: _AgentsDirOpt = _DEFAULT_AGENTS_DIR,
    resolve: Annotated[
        bool,
        typer.Option("--resolve", help="Verifica registro de cada recurso declarado"),
    ] = False,
    skills_dir: _SkillsDirOpt = _DEFAULT_SKILLS_DIR,
) -> None:
    """Mostra detalhes do manifest de um agente."""
    registry = AgentRegistry(agents_dir)
    manifests = {m.nome: m for m in registry.list_manifests()}
    if nome not in manifests:
        typer.echo(f"Agente '{nome}' nao encontrado em {agents_dir}.", err=True)
        raise typer.Exit(code=1)

    m = manifests[nome]
    typer.echo(f"Nome:           {m.nome}")
    typer.echo(f"Tipo:           {m.tipo}")
    typer.echo(f"Setor:          {m.setor}")
    typer.echo(f"Execucao:       {m.execucao}")
    typer.echo(f"Modelo minimo:  {m.modelo_minimo.value}")
    if m.endpoint:
        typer.echo(f"Endpoint:       {m.endpoint}")
    typer.echo(f"Vault scope:    {m.vault_scope}")
    typer.echo(f"Descricao:      {m.descricao}")
    typer.echo(f"Quando usar:    {m.quando_usar}")
    typer.echo(f"Inputs:         {', '.join(m.inputs_obrigatorios) or '(nenhum)'}")
    typer.echo(f"Skills:         {', '.join(m.capacidades_externas.skills) or '(nenhuma)'}")
    typer.echo(f"MCPs:           {', '.join(m.capacidades_externas.mcps) or '(nenhuma)'}")
    typer.echo(f"RAG:            {m.capacidades_externas.rag or '(nenhum)'}")
    if m.especialistas:
        typer.echo(f"Especialistas:  {', '.join(m.especialistas)}")

    if resolve:
        from stella.framework.errors import SkillNotFoundError
        from stella.framework.resources.skills_registry import SkillsRegistry

        typer.echo("\nResolução de recursos:")
        sk_reg = SkillsRegistry(skills_dir)
        for skill_id in m.capacidades_externas.skills:
            try:
                sk_reg.get(skill_id)
                typer.echo(f"  ✓ skill '{skill_id}' registrada")
            except SkillNotFoundError:
                typer.echo(f"  ✗ skill '{skill_id}' FALTA em {skills_dir}")
        for mcp_nome in m.capacidades_externas.mcps:
            typer.echo(f"  ? MCP '{mcp_nome}' (precisa registrar em runtime)")
        if m.capacidades_externas.rag:
            typer.echo(f"  ? RAG '{m.capacidades_externas.rag}' (precisa registrar em runtime)")


_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


@agent_app.command("new")
def new_agent(
    nome: Annotated[str, typer.Argument(help="Nome do novo agente (snake_case)")],
    setor: Annotated[str, typer.Option("--setor", help="Setor (marketing, financeiro, etc)")],
    tipo: Annotated[
        str, typer.Option("--tipo", help="Tipo: 'coordenador' ou 'especialista'")
    ] = "especialista",
    agents_dir: _AgentsDirOpt = _DEFAULT_AGENTS_DIR,
) -> None:
    """Cria scaffolding de um novo agente."""
    if tipo not in ("coordenador", "especialista"):
        typer.echo(f"--tipo deve ser 'coordenador' ou 'especialista', recebi '{tipo}'.", err=True)
        raise typer.Exit(code=1)

    pasta = agents_dir / nome
    if pasta.exists():
        typer.echo(f"Pasta {pasta} ja existe — nao sobrescrevo.", err=True)
        raise typer.Exit(code=1)

    pasta.mkdir(parents=True)
    substituicoes = {"NOME": nome, "SETOR": setor, "TIPO": tipo}
    _criar_arquivo(pasta / "__init__.py", _TEMPLATES_DIR / "__init__.py.tmpl", substituicoes)
    _criar_arquivo(pasta / "agent.py", _TEMPLATES_DIR / "agent.py.tmpl", substituicoes)
    _criar_arquivo(pasta / "manifest.yaml", _TEMPLATES_DIR / "manifest.yaml.tmpl", substituicoes)

    typer.echo(f"Agente '{nome}' criado em {pasta}.")
    typer.echo("Proximos passos:")
    typer.echo(f"  1. Editar {pasta}/manifest.yaml (descricao + capacidades)")
    typer.echo(f"  2. Implementar execute() em {pasta}/agent.py")
    typer.echo("  3. Adicionar testes em tests/agents/<nome>/test_agent.py")


def _criar_arquivo(destino: Path, template: Path, substituicoes: dict[str, str]) -> None:
    """Le template, substitui placeholders {CHAVE} e grava no destino."""
    conteudo = template.read_text(encoding="utf-8").format(**substituicoes)
    destino.write_text(conteudo, encoding="utf-8")
