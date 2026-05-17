from unittest.mock import MagicMock

from typer.testing import CliRunner

from stella.framework.errors import (
    AgentNotFoundError,
    AgentTimeoutError,
    AgentUnavailableError,
    BudgetExceededError,
    DelegationDepthExceeded,
    FrameworkError,
    ManifestError,
    MCPError,
    QualityReviewFailed,
    SkillNotFoundError,
)
from stella.frontends.cli import _traduzir_erro_jarvis, app

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


def test_traduzir_agent_not_found_jarvis() -> None:
    erro = AgentNotFoundError("Agente 'x' nao registrado")
    msg = _traduzir_erro_jarvis(erro)
    assert msg.startswith("Senhor,")
    assert "agente" in msg.lower()


def test_traduzir_agent_unavailable_sugere_iniciar_servidor() -> None:
    erro = AgentUnavailableError("Agent HTTP offline")
    msg = _traduzir_erro_jarvis(erro)
    assert msg.startswith("Senhor,")
    assert "offline" in msg.lower()


def test_traduzir_agent_timeout_indica_demora() -> None:
    erro = AgentTimeoutError("nao respondeu em 60s")
    msg = _traduzir_erro_jarvis(erro)
    assert "tempo" in msg.lower() or "demor" in msg.lower()


def test_traduzir_manifest_error_explica_config() -> None:
    erro = ManifestError("YAML invalido em manifest.yaml")
    msg = _traduzir_erro_jarvis(erro)
    assert "manifest" in msg.lower() or "configurac" in msg.lower()


def test_traduzir_delegation_depth_exceeded_indica_loop() -> None:
    erro = DelegationDepthExceeded("profundidade 5")
    msg = _traduzir_erro_jarvis(erro)
    assert "loop" in msg.lower() or "profund" in msg.lower()


def test_traduzir_budget_exceeded_indica_teto() -> None:
    erro = BudgetExceededError("teto US$100")
    msg = _traduzir_erro_jarvis(erro)
    assert "teto" in msg.lower() or "orcament" in msg.lower() or "limite" in msg.lower()


def test_traduzir_quality_review_failed_indica_revisao() -> None:
    erro = QualityReviewFailed("reprovado 2x")
    msg = _traduzir_erro_jarvis(erro)
    assert "revis" in msg.lower() or "qualidade" in msg.lower()


def test_traduzir_skill_not_found_indica_skill() -> None:
    erro = SkillNotFoundError("skill 'x' nao registrada")
    msg = _traduzir_erro_jarvis(erro)
    assert "skill" in msg.lower()


def test_traduzir_mcp_error_indica_integracao() -> None:
    erro = MCPError("MCP brave-search falhou")
    msg = _traduzir_erro_jarvis(erro)
    assert "mcp" in msg.lower() or "integrac" in msg.lower()


def test_traduzir_framework_error_generico() -> None:
    """Subclasse desconhecida cai no fallback."""

    class ErroNovo(FrameworkError):
        pass

    erro = ErroNovo("algo deu errado")
    msg = _traduzir_erro_jarvis(erro)
    assert msg.startswith("Senhor,")
    assert "algo deu errado" in msg
