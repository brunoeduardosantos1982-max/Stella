"""F4 — aceitação do fio carrossel: mensagem -> daemon -> cérebro (mockado).

Prova que uma mensagem de carrossel faz o daemon invocar o `claude -p` com a
PERSONA_CARROSSEL e o Opus, sem gastar uma sessão real nem tocar no estado sticky.
A E2E viva (Telegram -> cérebro -> comandos stella) é confirmada manualmente.
"""

from pathlib import Path

from stella.corpo import daemon_telegram as daemon


def test_mensagem_carrossel_invoca_cerebro_com_persona_carrossel(monkeypatch, tmp_path):
    capturado: dict[str, list[str]] = {}

    def fake_rodar(args: list[str]) -> tuple[int, str, str]:
        capturado["args"] = args
        return (0, '{"result": "feito"}', "")

    monkeypatch.setattr(daemon, "_conteudo_ativo", lambda: False)
    monkeypatch.setattr(daemon, "_ler_sessao", lambda: "")
    monkeypatch.setattr(daemon, "CONTEUDO_STATE", tmp_path / "conteudo.json")
    monkeypatch.setattr(daemon, "_rodar_claude_json", fake_rodar)
    monkeypatch.setattr(daemon.shutil, "which", lambda _: "claude")

    resposta = daemon.executar_claude("Stella, faz um carrossel sobre agentes de IA")

    args = capturado["args"]
    # persona vai por arquivo (--append-system-prompt-file), não inline, senão mangla no claude.CMD
    assert "--append-system-prompt-file" in args
    persona = Path(args[args.index("--append-system-prompt-file") + 1]).read_text(encoding="utf-8")
    assert daemon.PERSONA_CARROSSEL in persona
    assert daemon.PERSONA_CONTEUDO not in persona  # é carrossel, não reel
    assert daemon.MODELO_OPUS in args
    assert resposta == "feito"
    # o modo carrossel ficou registrado no sticky
    assert daemon._modo_sticky() == "carrossel"
