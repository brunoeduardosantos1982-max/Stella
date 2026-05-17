from pathlib import Path

from typer.testing import CliRunner

from stella.framework.cli.agent_cli import agent_app

runner = CliRunner()


_MANIFEST_A = """\
nome: agente_a
tipo: especialista
setor: testes
descricao: agente alpha para testes do CLI
execucao: in_process
modelo_minimo: gemma
inputs_obrigatorios: []
exemplo_uso: {}
quando_usar: testes do CLI agent
capacidades_externas: {}
vault_scope: "testes/**"
"""


_MANIFEST_B = """\
nome: coord_b
tipo: coordenador
setor: testes
descricao: coordenador beta para testes do CLI
execucao: http
endpoint: "http://localhost:9000"
modelo_minimo: sonnet
inputs_obrigatorios: [acao]
exemplo_uso:
  acao: ping
quando_usar: testes do CLI agent
capacidades_externas: {}
vault_scope: "testes/**"
"""


def _escrever(agents_dir: Path, nome: str, yaml: str) -> None:
    p = agents_dir / nome
    p.mkdir(parents=True)
    (p / "manifest.yaml").write_text(yaml, encoding="utf-8")


def test_agent_list_mostra_agentes_descobertos(tmp_path: Path) -> None:
    _escrever(tmp_path, "agente_a", _MANIFEST_A)
    _escrever(tmp_path, "coord_b", _MANIFEST_B)

    result = runner.invoke(agent_app, ["list", "--agents-dir", str(tmp_path)])
    assert result.exit_code == 0
    assert "agente_a" in result.stdout
    assert "coord_b" in result.stdout


def test_agent_list_pasta_vazia_mostra_mensagem(tmp_path: Path) -> None:
    result = runner.invoke(agent_app, ["list", "--agents-dir", str(tmp_path)])
    assert result.exit_code == 0
    assert "nenhum" in result.stdout.lower() or "vazio" in result.stdout.lower()


def test_agent_list_mostra_tipo_e_setor(tmp_path: Path) -> None:
    _escrever(tmp_path, "coord_b", _MANIFEST_B)
    result = runner.invoke(agent_app, ["list", "--agents-dir", str(tmp_path)])
    assert "coordenador" in result.stdout
    assert "testes" in result.stdout
