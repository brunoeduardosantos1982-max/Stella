from pathlib import Path

import pytest

from stella.framework.agent import Agent, AgentOutput
from stella.framework.client import HttpAgentClient, InProcessClient
from stella.framework.errors import AgentNotFoundError
from stella.framework.manifest import AgentManifest
from stella.framework.registry import AgentRegistry

_MANIFEST_INPROC = """\
nome: agente_a
tipo: especialista
setor: testes
descricao: agente local de testes
execucao: in_process
modelo_minimo: gemma
inputs_obrigatorios: []
exemplo_uso: {}
quando_usar: apenas em testes
capacidades_externas: {}
vault_scope: "C04 Claude Obsidian/Stella-workspace/testes/**"
"""

_MANIFEST_HTTP = """\
nome: coord_remoto
tipo: coordenador
setor: ecommerce
descricao: agente remoto de testes via HTTP
execucao: http
endpoint: "http://localhost:9999"
modelo_minimo: sonnet
inputs_obrigatorios: [acao]
exemplo_uso:
  acao: ping
quando_usar: testes do registry com agentes HTTP
capacidades_externas: {}
vault_scope: "C04 Claude Obsidian/Stella-workspace/testes/**"
"""


def _escrever_manifest(agents_dir: Path, nome_pasta: str, yaml: str) -> None:
    pasta = agents_dir / nome_pasta
    pasta.mkdir(parents=True)
    (pasta / "manifest.yaml").write_text(yaml, encoding="utf-8")


class _AgenteEcho(Agent):
    def execute(self, input: dict) -> AgentOutput:
        return AgentOutput(resultado={"echo": input})


def _builder_de_teste(manifest: AgentManifest) -> Agent:
    return _AgenteEcho()


def test_registry_descobre_manifests_da_pasta_agents(tmp_path: Path) -> None:
    _escrever_manifest(tmp_path, "agente_a", _MANIFEST_INPROC)
    _escrever_manifest(tmp_path, "coord_remoto", _MANIFEST_HTTP)
    reg = AgentRegistry(tmp_path)
    nomes = set(reg.list_nomes())
    assert nomes == {"agente_a", "coord_remoto"}


def test_registry_lista_manifests(tmp_path: Path) -> None:
    _escrever_manifest(tmp_path, "agente_a", _MANIFEST_INPROC)
    reg = AgentRegistry(tmp_path)
    manifests = reg.list_manifests()
    assert len(manifests) == 1
    assert manifests[0].nome == "agente_a"


def test_registry_pasta_sem_manifest_e_ignorada_com_warning(tmp_path: Path) -> None:
    _escrever_manifest(tmp_path, "agente_a", _MANIFEST_INPROC)
    (tmp_path / "pasta_sem_manifest").mkdir()
    reg = AgentRegistry(tmp_path)
    assert reg.list_nomes() == ["agente_a"]


def test_registry_ignora_pycache_e_pastas_internas_sem_warning(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """Pastas internas do Python (__pycache__, .git, etc) não devem gerar warning."""
    import logging

    _escrever_manifest(tmp_path, "agente_a", _MANIFEST_INPROC)
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / ".cache").mkdir()

    with caplog.at_level(logging.WARNING, logger="stella.framework.registry"):
        reg = AgentRegistry(tmp_path)

    assert reg.list_nomes() == ["agente_a"]
    avisos = [r.message for r in caplog.records if r.levelno >= logging.WARNING]
    assert all("__pycache__" not in m and ".cache" not in m for m in avisos), avisos


def test_registry_manifest_invalido_e_pulado(tmp_path: Path) -> None:
    _escrever_manifest(tmp_path, "agente_a", _MANIFEST_INPROC)
    _escrever_manifest(tmp_path, "agente_quebrado", "nome: x\ntipo: especialista\nsetor: x\n")
    reg = AgentRegistry(tmp_path)
    assert reg.list_nomes() == ["agente_a"]


def test_registry_pasta_inexistente_da_registry_vazio(tmp_path: Path) -> None:
    reg = AgentRegistry(tmp_path / "nao-existe")
    assert reg.list_nomes() == []


def test_registry_get_inprocess_requer_bind_builder(tmp_path: Path) -> None:
    _escrever_manifest(tmp_path, "agente_a", _MANIFEST_INPROC)
    reg = AgentRegistry(tmp_path)
    with pytest.raises(RuntimeError, match="bind_builder"):
        reg.get("agente_a")


def test_registry_get_inprocess_usa_builder_e_devolve_inprocess_client(
    tmp_path: Path,
) -> None:
    _escrever_manifest(tmp_path, "agente_a", _MANIFEST_INPROC)
    reg = AgentRegistry(tmp_path)
    reg.bind_builder(_builder_de_teste)
    client = reg.get("agente_a")
    assert isinstance(client, InProcessClient)
    assert client.manifest().nome == "agente_a"


def test_registry_get_http_devolve_http_client(tmp_path: Path) -> None:
    _escrever_manifest(tmp_path, "coord_remoto", _MANIFEST_HTTP)
    reg = AgentRegistry(tmp_path)
    client = reg.get("coord_remoto")
    assert isinstance(client, HttpAgentClient)
    assert client.manifest().nome == "coord_remoto"


def test_registry_get_cacheia_client_por_nome(tmp_path: Path) -> None:
    _escrever_manifest(tmp_path, "coord_remoto", _MANIFEST_HTTP)
    reg = AgentRegistry(tmp_path)
    c1 = reg.get("coord_remoto")
    c2 = reg.get("coord_remoto")
    assert c1 is c2


def test_registry_get_levanta_agent_not_found(tmp_path: Path) -> None:
    reg = AgentRegistry(tmp_path)
    with pytest.raises(AgentNotFoundError, match="nao-existe"):
        reg.get("nao-existe")
