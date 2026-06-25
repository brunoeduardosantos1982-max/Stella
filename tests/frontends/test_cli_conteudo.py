from typer.testing import CliRunner

from stella.domain.registro_keywords import RegistroKeywords
from stella.frontends.cli import app

runner = CliRunner()


def test_conteudo_listar_imprime_posts(monkeypatch, tmp_path):
    reg = RegistroKeywords()
    reg.registrar_post("VITRINE", "2026-06-24-vitrine", slug="s")
    reg_path = tmp_path / "registro-keywords.json"
    reg.salvar(reg_path)
    monkeypatch.setattr("stella.frontends.cli._registro_path", lambda: reg_path)
    monkeypatch.setattr("stella.frontends.cli._fab_dir", lambda: tmp_path)
    res = runner.invoke(app, ["conteudo-listar", "VITRINE"])
    assert res.exit_code == 0
    assert "2026-06-24-vitrine" in res.stdout
