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


def test_agent_show_mostra_manifest_completo(tmp_path: Path) -> None:
    _escrever(tmp_path, "agente_a", _MANIFEST_A)
    result = runner.invoke(agent_app, ["show", "agente_a", "--agents-dir", str(tmp_path)])
    assert result.exit_code == 0
    assert "agente_a" in result.stdout
    assert "especialista" in result.stdout
    assert "agente alpha para testes" in result.stdout
    assert "in_process" in result.stdout


def test_agent_show_http_mostra_endpoint(tmp_path: Path) -> None:
    _escrever(tmp_path, "coord_b", _MANIFEST_B)
    result = runner.invoke(agent_app, ["show", "coord_b", "--agents-dir", str(tmp_path)])
    assert "http://localhost:9000" in result.stdout


def test_agent_show_nome_inexistente_devolve_erro(tmp_path: Path) -> None:
    result = runner.invoke(agent_app, ["show", "nao-existe", "--agents-dir", str(tmp_path)])
    assert result.exit_code != 0


def test_agent_new_cria_estrutura_de_pastas(tmp_path: Path) -> None:
    result = runner.invoke(
        agent_app,
        [
            "new",
            "agente_novo",
            "--setor",
            "marketing",
            "--tipo",
            "especialista",
            "--agents-dir",
            str(tmp_path),
        ],
    )
    assert result.exit_code == 0, result.stdout
    assert (tmp_path / "agente_novo" / "__init__.py").exists()
    assert (tmp_path / "agente_novo" / "agent.py").exists()
    assert (tmp_path / "agente_novo" / "manifest.yaml").exists()


def test_agent_new_manifest_tem_setor_e_tipo_substituidos(tmp_path: Path) -> None:
    runner.invoke(
        agent_app,
        [
            "new",
            "agente_x",
            "--setor",
            "financeiro",
            "--tipo",
            "coordenador",
            "--agents-dir",
            str(tmp_path),
        ],
    )
    manifest = (tmp_path / "agente_x" / "manifest.yaml").read_text(encoding="utf-8")
    assert "nome: agente_x" in manifest
    assert "tipo: coordenador" in manifest
    assert "setor: financeiro" in manifest


def test_agent_new_agent_py_tem_classe_agent_substituida(tmp_path: Path) -> None:
    runner.invoke(
        agent_app,
        [
            "new",
            "agente_y",
            "--setor",
            "copy",
            "--tipo",
            "especialista",
            "--agents-dir",
            str(tmp_path),
        ],
    )
    agent_py = (tmp_path / "agente_y" / "agent.py").read_text(encoding="utf-8")
    assert "Agente agente_y" in agent_py
    assert "class Agent(BaseAgent)" in agent_py


def test_agent_new_pasta_ja_existe_devolve_erro(tmp_path: Path) -> None:
    (tmp_path / "agente_dup").mkdir()
    result = runner.invoke(
        agent_app,
        [
            "new",
            "agente_dup",
            "--setor",
            "x",
            "--tipo",
            "especialista",
            "--agents-dir",
            str(tmp_path),
        ],
    )
    assert result.exit_code != 0
