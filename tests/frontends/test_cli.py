from unittest.mock import MagicMock

from typer.testing import CliRunner

from stella.frontends.cli import app

runner = CliRunner()


def test_anota_chama_capturar_ideia(monkeypatch, vault_tmp) -> None:
    fake_resultado = MagicMock()
    fake_resultado.path = "A00 Inbox/2026-05-15 14-32 — Revisar copy.md"
    fake_resultado.titulo = "Revisar copy"

    fake_stella = MagicMock()
    fake_stella.capturar_ideia.execute.return_value = fake_resultado

    monkeypatch.setattr("stella.frontends.cli._build_stella_para_cli", lambda: fake_stella)

    result = runner.invoke(app, ["anota", "revisar copy do centro viagens"])

    assert result.exit_code == 0
    assert "Anotado" in result.stdout
    assert "Revisar copy" in result.stdout
    fake_stella.capturar_ideia.execute.assert_called_once()


def test_pergunta_chama_responder_projeto(monkeypatch, vault_tmp) -> None:
    fake_resultado = MagicMock()
    fake_resultado.resposta = "Resposta sobre Centro Viagens"
    fake_resultado.fontes = ["B01 Projetos/Centro Viagens.md"]

    fake_stella = MagicMock()
    fake_stella.responder_projeto.execute.return_value = fake_resultado

    monkeypatch.setattr("stella.frontends.cli._build_stella_para_cli", lambda: fake_stella)

    result = runner.invoke(app, ["pergunta", "Centro Viagens", "o que esta aberto"])

    assert result.exit_code == 0
    assert "Resposta sobre Centro Viagens" in result.stdout
    fake_stella.responder_projeto.execute.assert_called_once()


def test_anota_propaga_erro_de_usecase(monkeypatch, vault_tmp) -> None:
    from stella.usecases.base import EntradaInvalida

    fake_stella = MagicMock()
    fake_stella.capturar_ideia.execute.side_effect = EntradaInvalida("texto vazio")

    monkeypatch.setattr("stella.frontends.cli._build_stella_para_cli", lambda: fake_stella)

    result = runner.invoke(app, ["anota", "   "])

    assert result.exit_code != 0
    assert "não consegui anotar" in result.stdout or "não consegui anotar" in (result.stderr or "")
