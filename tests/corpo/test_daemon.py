from pathlib import Path

from stella.corpo import daemon_telegram as daemon


def _runtime() -> daemon.DaemonRuntime:
    return daemon.DaemonRuntime(started_at=1_700_000_000.0)


def _secrets() -> daemon.TelegramSecrets:
    return daemon.TelegramSecrets(bot_token="token-fake", chat_id="123")


def _update(chat_id: int, text: str) -> dict[str, object]:
    return {"message": {"chat": {"id": chat_id}, "text": text}}


def test_update_chat_nao_autorizado_e_ignorado(monkeypatch, tmp_path: Path) -> None:
    enviados: list[str] = []
    monkeypatch.setattr(daemon, "send_message", lambda token, chat_id, text: enviados.append(text))
    monkeypatch.setattr(daemon, "send_chat_action", lambda token, chat_id: None)

    daemon.process_update(
        _update(999, "execute algo"),
        _secrets(),
        _runtime(),
        run_claude=lambda texto: "nao deveria executar",
        log_path=tmp_path / "daemon.log",
    )

    assert enviados == []
    assert "chat_id=999" in (tmp_path / "daemon.log").read_text(encoding="utf-8")


def test_mensagem_autorizada_executa_claude_e_envia_stdout(monkeypatch) -> None:
    enviados: list[str] = []
    acoes: list[str] = []
    executados: list[str] = []

    monkeypatch.setattr(daemon, "send_message", lambda token, chat_id, text: enviados.append(text))
    monkeypatch.setattr(daemon, "send_chat_action", lambda token, chat_id: acoes.append(chat_id))

    def fake_claude(texto: str) -> str:
        executados.append(texto)
        return "resposta do claude"

    runtime = _runtime()
    daemon.process_update(
        _update(123, "organize meu dia"), _secrets(), runtime, run_claude=fake_claude
    )

    assert executados == ["organize meu dia"]
    assert enviados == ["resposta do claude"]
    assert acoes == ["123"]
    assert runtime.last_execution is not None


def test_resposta_longa_e_fatiada_em_partes_de_ate_4000() -> None:
    partes = daemon.split_telegram_text("a" * 9005)

    assert len(partes) == 3
    assert all(len(parte) <= 4000 for parte in partes)
    assert "".join(partes) == "a" * 9005


def test_ping_responde_sem_chamar_subprocess(monkeypatch) -> None:
    enviados: list[str] = []
    monkeypatch.setattr(daemon, "send_message", lambda token, chat_id, text: enviados.append(text))

    def nao_chamar(texto: str) -> str:
        raise AssertionError("Claude nao deveria ser chamado")

    daemon.process_update(_update(123, "/ping"), _secrets(), _runtime(), run_claude=nao_chamar)

    assert len(enviados) == 1
    assert enviados[0].startswith("Stella online_")
