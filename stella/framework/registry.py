"""AgentRegistry — discovery e lookup de agentes.

Escaneia stella/agents/*/manifest.yaml na construcao. Cada manifest valido
fica indexado por nome. A construcao do AgentClient e LAZY: so acontece
quando alguem chama get(nome). Isso permite o padrao bind_builder() para
evitar ciclo Registry -> Builder -> Registry.

- Agente HTTP -> HttpAgentClient direto (nao precisa de builder).
- Agente in-process -> precisa builder injetado via bind_builder().
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from stella.framework.agent import Agent
from stella.framework.client import AgentClient, HttpAgentClient, InProcessClient
from stella.framework.errors import AgentNotFoundError, ManifestError
from stella.framework.manifest import AgentManifest, load_manifest

_logger = logging.getLogger(__name__)

BuilderFunc = Callable[[AgentManifest], Agent]


class AgentRegistry:
    """Indice de agentes descobertos por scan de manifests."""

    def __init__(self, agents_dir: Path) -> None:
        self._dir = Path(agents_dir)
        self._manifests: dict[str, AgentManifest] = {}
        self._clientes: dict[str, AgentClient] = {}
        self._builder: BuilderFunc | None = None
        self._scan()

    def _scan(self) -> None:
        if not self._dir.exists():
            return
        for pasta in sorted(p for p in self._dir.iterdir() if p.is_dir()):
            # Pular pastas internas (__pycache__, .git, .venv, etc) sem warning —
            # nunca foram agentes, são artefatos de tooling.
            if pasta.name.startswith(("__", ".")):
                continue
            manifest_path = pasta / "manifest.yaml"
            if not manifest_path.exists():
                _logger.warning("Pasta sem manifest.yaml ignorada: %s", pasta.name)
                continue
            try:
                manifest = load_manifest(manifest_path)
            except ManifestError as e:
                _logger.warning("Manifest invalido em %s: %s", pasta.name, e)
                continue
            self._manifests[manifest.nome] = manifest

    def bind_builder(self, builder: BuilderFunc) -> None:
        """Injeta a funcao build_agent. Necessario para agentes in_process.

        Padrao em duas fases: Stella constroi Registry, depois constroi
        FrameworkDeps (que referencia o Registry), depois chama
        registry.bind_builder(lambda m: build_agent(m, deps)).
        """
        self._builder = builder

    def list_nomes(self) -> list[str]:
        return list(self._manifests.keys())

    def list_manifests(self) -> list[AgentManifest]:
        return list(self._manifests.values())

    def get(self, nome: str) -> AgentClient:
        if nome not in self._manifests:
            raise AgentNotFoundError(
                f"Agente '{nome}' nao registrado. Conhecidos: {self.list_nomes()}"
            )
        if nome in self._clientes:
            return self._clientes[nome]

        manifest = self._manifests[nome]
        cliente: AgentClient
        if manifest.execucao == "http":
            cliente = HttpAgentClient(manifest=manifest)
        else:
            if self._builder is None:
                raise RuntimeError(
                    f"Agente in-process '{nome}' requer builder injetado. "
                    "Chame registry.bind_builder(build_func) antes de get()."
                )
            agent = self._builder(manifest)
            cliente = InProcessClient(agent=agent, manifest=manifest)

        self._clientes[nome] = cliente
        return cliente
