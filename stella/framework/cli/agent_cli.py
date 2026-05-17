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
