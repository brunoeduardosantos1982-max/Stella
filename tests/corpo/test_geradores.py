"""Roteamento de geradores de conteúdo (2026-09-28).

Bug: o modo conteúdo do daemon dispara por palavra solta (pauta, roteiro, conteúdo) e é
fixo no @brunoe.santos. Pedido do canal brujosie caía nele, em Opus, com a persona e a
sessão erradas. Agora o gerador com dono é roteado antes e não passa pelo Claude do chat.
"""

from datetime import date
from pathlib import Path

from stella.corpo import daemon_telegram as daemon
from stella.corpo import geradores
from stella.corpo.geradores import (
    interpretar_pedido_brujosie,
    responder_brujosie,
    rotear_gerador,
)

HOJE = date(2026, 9, 28)  # segunda


def test_roteia_brujosie_em_varias_grafias() -> None:
    for texto in (
        "brujosie engasgo",
        "pauta brujosie: choque elétrico",
        "/brujosie abelhas",
        "Bru Josie afogamento",
        "conteúdo pro @brujosie.preparados sobre enchente",
    ):
        assert rotear_gerador(texto) == "brujosie", texto


def test_pedido_de_conteudo_de_outro_canal_nao_e_roubado() -> None:
    # sem o nome do gerador, continua no fluxo normal (modo conteúdo do @brunoe.santos)
    for texto in ("cria um roteiro sobre vendas", "me manda a pauta de hoje", "bom dia"):
        assert rotear_gerador(texto) is None, texto


def test_interpreta_tema_simples() -> None:
    p = interpretar_pedido_brujosie("brujosie engasgo", hoje=HOJE)
    assert p.tema == "engasgo"
    assert p.data is None


def test_interpreta_enfeites_e_dois_pontos() -> None:
    p = interpretar_pedido_brujosie("Pauta brujosie: tema choque elétrico", hoje=HOJE)
    assert p.tema == "choque elétrico"


def test_interpreta_pedido_falado_com_stella_e_preparados() -> None:
    p = interpretar_pedido_brujosie(
        "Stella, quero uma pauta pro brujosie preparados sobre afogamento", hoje=HOJE
    )
    assert p.tema == "afogamento"
    p = interpretar_pedido_brujosie("brujosie.preparados picada de escorpião", hoje=HOJE)
    assert p.tema == "picada de escorpião"


def test_interpreta_data_numerica_e_amanha() -> None:
    assert interpretar_pedido_brujosie("brujosie afogamento 02/10", hoje=HOJE).data == "2026-10-02"
    p = interpretar_pedido_brujosie("brujosie abelhas amanhã", hoje=HOJE)
    assert (p.tema, p.data) == ("abelhas", "2026-09-29")
    p = interpretar_pedido_brujosie("brujosie enchente depois de amanhã", hoje=HOJE)
    assert (p.tema, p.data) == ("enchente", "2026-09-30")


def test_data_invalida_nao_quebra() -> None:
    p = interpretar_pedido_brujosie("brujosie queimadura 31/02", hoje=HOJE)
    assert p.data is None
    assert p.tema is not None and p.tema.startswith("queimadura")


def test_sem_tema_pede_o_tema_e_nao_dispara() -> None:
    chamadas: list[list[str]] = []
    resposta = responder_brujosie("brujosie", popen=chamadas.append, hoje=HOJE)
    assert chamadas == []
    assert "tema" in resposta


def test_dispara_rotina_com_tema_e_data(tmp_path: Path) -> None:
    script = tmp_path / "rotina-pauta.ps1"
    script.write_text("# fake", encoding="utf-8")
    chamadas: list[list[str]] = []
    resposta = responder_brujosie(
        "brujosie engasgo 01/10", popen=chamadas.append, script=script, hoje=HOJE
    )
    assert len(chamadas) == 1
    args = chamadas[0]
    assert args[0] == "powershell.exe"
    assert args[args.index("-File") + 1] == str(script)
    assert args[args.index("-Tema") + 1] == "engasgo"
    assert args[args.index("-Data") + 1] == "2026-10-01"
    assert "engasgo" in resposta and "01/10" in resposta
    assert "aprovação" in resposta


def test_tema_nao_vira_flag_do_powershell(tmp_path: Path) -> None:
    script = tmp_path / "rotina-pauta.ps1"
    script.write_text("# fake", encoding="utf-8")
    chamadas: list[list[str]] = []
    responder_brujosie("brujosie -Command evil", popen=chamadas.append, script=script, hoje=HOJE)
    assert chamadas[0][chamadas[0].index("-Tema") + 1] == "Command evil"


def test_script_ausente_nao_dispara(tmp_path: Path) -> None:
    chamadas: list[list[str]] = []
    resposta = responder_brujosie(
        "brujosie engasgo", popen=chamadas.append, script=tmp_path / "nao-existe.ps1", hoje=HOJE
    )
    assert chamadas == []
    assert "não achei" in resposta


def test_tema_muito_longo_e_cortado() -> None:
    p = interpretar_pedido_brujosie("brujosie " + "x" * 500, hoje=HOJE)
    assert p.tema is not None and len(p.tema) == geradores.TEMA_MAX


# --- Integração com o daemon: o Claude do chat NUNCA é chamado ---------------------


def _update(texto: str) -> dict[str, object]:
    return {"message": {"chat": {"id": 123}, "text": texto}}


def test_daemon_roteia_brujosie_sem_chamar_claude_nem_tocar_estado(monkeypatch) -> None:
    enviados: list[str] = []
    monkeypatch.setattr(daemon, "send_message", lambda token, chat_id, text: enviados.append(text))
    monkeypatch.setattr(
        daemon, "responder_gerador", lambda nome, texto: f"gerador {nome} recebeu: {texto}"
    )

    def nao_chamar(texto: str) -> str:
        raise AssertionError("o Claude do chat nao deveria ser chamado")

    def nao_tocar() -> None:
        raise AssertionError("o estado do modo conteudo nao deveria ser tocado")

    monkeypatch.setattr(daemon, "_ativar_conteudo", lambda modo="reel": nao_tocar())
    monkeypatch.setattr(daemon, "resetar_sessao", nao_tocar)

    runtime = daemon.DaemonRuntime(started_at=1_700_000_000.0)
    daemon.process_update(
        _update("pauta brujosie engasgo"),
        daemon.TelegramSecrets(bot_token="token-fake", chat_id="123"),
        runtime,
        run_claude=nao_chamar,
    )

    assert enviados == ["gerador brujosie recebeu: pauta brujosie engasgo"]
    assert runtime.last_execution is not None


def test_daemon_falha_do_gerador_avisa_e_nao_cai_no_conteudo_do_bruno(
    monkeypatch, tmp_path: Path
) -> None:
    enviados: list[str] = []
    monkeypatch.setattr(daemon, "send_message", lambda token, chat_id, text: enviados.append(text))

    def quebrar(nome: str, texto: str) -> str:
        raise OSError("powershell sumiu")

    monkeypatch.setattr(daemon, "responder_gerador", quebrar)

    def nao_chamar(texto: str) -> str:
        raise AssertionError("nao deveria cair no Claude do chat")

    daemon.process_update(
        _update("brujosie engasgo"),
        daemon.TelegramSecrets(bot_token="token-fake", chat_id="123"),
        daemon.DaemonRuntime(started_at=1_700_000_000.0),
        run_claude=nao_chamar,
        log_path=tmp_path / "daemon.log",  # nunca o log de producao
    )

    assert len(enviados) == 1
    assert "falhou" in enviados[0]
    assert "gerador brujosie falhou" in (tmp_path / "daemon.log").read_text(encoding="utf-8")


def test_daemon_pedido_de_conteudo_comum_segue_para_o_claude(monkeypatch) -> None:
    enviados: list[str] = []
    executados: list[str] = []
    monkeypatch.setattr(daemon, "send_message", lambda token, chat_id, text: enviados.append(text))
    monkeypatch.setattr(daemon, "send_chat_action", lambda token, chat_id: None)

    def fake_claude(texto: str) -> str:
        executados.append(texto)
        return "ok"

    daemon.process_update(
        _update("cria um roteiro sobre vendas"),
        daemon.TelegramSecrets(bot_token="token-fake", chat_id="123"),
        daemon.DaemonRuntime(started_at=1_700_000_000.0),
        run_claude=fake_claude,
    )

    assert executados == ["cria um roteiro sobre vendas"]
