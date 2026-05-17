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
