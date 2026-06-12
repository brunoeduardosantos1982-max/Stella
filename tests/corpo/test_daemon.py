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


def _update_voz(chat_id: int, file_id: str = "voz-001") -> dict[str, object]:
    return {"message": {"chat": {"id": chat_id}, "voice": {"file_id": file_id}}}


def test_audio_autorizado_transcreve_executa_ecoa_e_fala(monkeypatch, tmp_path: Path) -> None:
    enviados: list[str] = []
    executados: list[str] = []
    falados: list[str] = []
    audios_enviados: list[Path] = []

    monkeypatch.setattr(daemon, "send_message", lambda token, chat_id, text: enviados.append(text))
    monkeypatch.setattr(daemon, "send_chat_action", lambda token, chat_id: None)
    monkeypatch.setattr(
        daemon,
        "baixar_arquivo_voz",
        lambda token, file_id, destino_dir: destino_dir / "voz.oga",
    )
    monkeypatch.setattr(
        daemon, "send_voice", lambda token, chat_id, caminho: audios_enviados.append(caminho)
    )

    def fake_claude(texto: str) -> str:
        executados.append(texto)
        return "site no ar"

    def fake_sintetizar(texto: str, destino: Path) -> Path:
        falados.append(texto)
        return destino

    runtime = _runtime()
    daemon.process_update(
        _update_voz(123),
        _secrets(),
        runtime,
        run_claude=fake_claude,
        transcrever_audio=lambda caminho: "verifica o site da josie",
        sintetizar_fala=fake_sintetizar,
        log_path=tmp_path / "daemon.log",
    )

    assert executados == ["verifica o site da josie"]
    assert len(enviados) == 1
    assert 'Entendi: "verifica o site da josie"' in enviados[0]
    assert "site no ar" in enviados[0]
    assert falados == ["site no ar"]
    assert len(audios_enviados) == 1
    assert runtime.last_execution is not None


def test_falha_na_sintese_nao_derruba_resposta_de_texto(monkeypatch, tmp_path: Path) -> None:
    enviados: list[str] = []

    monkeypatch.setattr(daemon, "send_message", lambda token, chat_id, text: enviados.append(text))
    monkeypatch.setattr(daemon, "send_chat_action", lambda token, chat_id: None)
    monkeypatch.setattr(
        daemon,
        "baixar_arquivo_voz",
        lambda token, file_id, destino_dir: destino_dir / "voz.oga",
    )

    def sintese_quebrada(texto: str, destino: Path) -> Path:
        raise RuntimeError("edge-tts fora do ar")

    daemon.process_update(
        _update_voz(123),
        _secrets(),
        _runtime(),
        run_claude=lambda texto: "resposta ok",
        transcrever_audio=lambda caminho: "qualquer comando",
        sintetizar_fala=sintese_quebrada,
        log_path=tmp_path / "daemon.log",
    )

    assert len(enviados) == 1
    assert "resposta ok" in enviados[0]
    log = (tmp_path / "daemon.log").read_text(encoding="utf-8")
    assert "falha ao sintetizar voz" in log


def test_mensagem_de_texto_nao_gera_audio(monkeypatch) -> None:
    enviados: list[str] = []
    audios_enviados: list[Path] = []

    monkeypatch.setattr(daemon, "send_message", lambda token, chat_id, text: enviados.append(text))
    monkeypatch.setattr(daemon, "send_chat_action", lambda token, chat_id: None)
    monkeypatch.setattr(
        daemon, "send_voice", lambda token, chat_id, caminho: audios_enviados.append(caminho)
    )

    def nao_sintetizar(texto: str, destino: Path) -> Path:
        raise AssertionError("texto digitado nao deveria virar audio")

    daemon.process_update(
        _update(123, "organize meu dia"),
        _secrets(),
        _runtime(),
        run_claude=lambda texto: "feito",
        sintetizar_fala=nao_sintetizar,
    )

    assert enviados == ["feito"]
    assert audios_enviados == []


def test_audio_com_falha_de_transcricao_avisa_e_nao_executa(monkeypatch, tmp_path: Path) -> None:
    enviados: list[str] = []
    monkeypatch.setattr(daemon, "send_message", lambda token, chat_id, text: enviados.append(text))
    monkeypatch.setattr(daemon, "send_chat_action", lambda token, chat_id: None)
    monkeypatch.setattr(
        daemon,
        "baixar_arquivo_voz",
        lambda token, file_id, destino_dir: (_ for _ in ()).throw(ValueError("download falhou")),
    )

    def nao_chamar(texto: str) -> str:
        raise AssertionError("Claude nao deveria ser chamado")

    daemon.process_update(
        _update_voz(123),
        _secrets(),
        _runtime(),
        run_claude=nao_chamar,
        transcrever_audio=lambda caminho: "",
        log_path=tmp_path / "daemon.log",
    )

    assert len(enviados) == 1
    assert "áudio" in enviados[0]


def test_audio_de_chat_nao_autorizado_e_ignorado(monkeypatch, tmp_path: Path) -> None:
    enviados: list[str] = []
    monkeypatch.setattr(daemon, "send_message", lambda token, chat_id, text: enviados.append(text))

    def nao_baixar(token: str, file_id: str, destino_dir: Path) -> Path:
        raise AssertionError("nao deveria baixar audio de chat estranho")

    monkeypatch.setattr(daemon, "baixar_arquivo_voz", nao_baixar)

    daemon.process_update(
        _update_voz(999),
        _secrets(),
        _runtime(),
        run_claude=lambda texto: "nao deveria executar",
        log_path=tmp_path / "daemon.log",
    )

    assert enviados == []


def test_ping_responde_sem_chamar_subprocess(monkeypatch) -> None:
    enviados: list[str] = []
    monkeypatch.setattr(daemon, "send_message", lambda token, chat_id, text: enviados.append(text))

    def nao_chamar(texto: str) -> str:
        raise AssertionError("Claude nao deveria ser chamado")

    daemon.process_update(_update(123, "/ping"), _secrets(), _runtime(), run_claude=nao_chamar)

    assert len(enviados) == 1
    assert "Stella online_" in enviados[0]
