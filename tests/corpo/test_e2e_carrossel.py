"""F4 — aceitação do fio carrossel: mensagem -> daemon -> cérebro (mockado).

Prova que uma mensagem de carrossel faz o daemon invocar o `claude -p` com a
PERSONA_CARROSSEL e o Opus, sem gastar uma sessão real nem tocar no estado sticky.
A E2E viva (Telegram -> cérebro -> comandos stella) é confirmada manualmente.
"""

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

    blob = "\n".join(capturado["args"])
    assert daemon.PERSONA_CARROSSEL in blob
    assert daemon.PERSONA_CONTEUDO not in blob  # é carrossel, não reel
    assert daemon.MODELO_OPUS in capturado["args"]
    assert resposta == "feito"
    # o modo carrossel ficou registrado no sticky
    assert daemon._modo_sticky() == "carrossel"
