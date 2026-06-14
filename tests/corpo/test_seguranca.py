import json
import time
from pathlib import Path

from stella.corpo import seguranca


def _montar_vault(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    for pasta in seguranca.PASTAS_RAIZ:
        (vault / pasta).mkdir(parents=True)
    for rel in seguranca.ARQUIVOS_CRITICOS:
        caminho = vault / rel
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text("conteudo critico", encoding="utf-8")
    return vault


def _montar_cofres(tmp_path: Path) -> Path:
    cofres = tmp_path / "cofres"
    cofres.mkdir()
    for nome in seguranca.COFRES:
        (cofres / nome).write_text(json.dumps({"ok": True}), encoding="utf-8")
    return cofres


def test_vault_saudavel_gera_status_ok(monkeypatch, tmp_path: Path) -> None:
    vault = _montar_vault(tmp_path)
    cofres = _montar_cofres(tmp_path)
    monkeypatch.setattr(seguranca, "contar_daemon_rodando", lambda: 2)

    relatorio = seguranca.executar_verificacao(vault, cofres)

    assert relatorio.status == "✅ OK"
    assert relatorio.criticos == []
    assert relatorio.atencoes == []
    assert any("15/15" in info for info in relatorio.infos)


def test_pasta_raiz_sumida_e_critico(monkeypatch, tmp_path: Path) -> None:
    vault = _montar_vault(tmp_path)
    cofres = _montar_cofres(tmp_path)
    monkeypatch.setattr(seguranca, "contar_daemon_rodando", lambda: 1)
    (vault / "B01 Projetos").rmdir()

    relatorio = seguranca.executar_verificacao(vault, cofres)

    assert relatorio.status == "❌ Problema"
    assert any("B01 Projetos" in item for item in relatorio.criticos)


def test_arquivo_critico_vazio_e_critico(monkeypatch, tmp_path: Path) -> None:
    vault = _montar_vault(tmp_path)
    cofres = _montar_cofres(tmp_path)
    monkeypatch.setattr(seguranca, "contar_daemon_rodando", lambda: 1)
    (vault / seguranca.ARQUIVOS_CRITICOS[0]).write_text("", encoding="utf-8")

    relatorio = seguranca.executar_verificacao(vault, cofres)

    assert any("vazio" in item for item in relatorio.criticos)


def test_cofre_corrompido_e_critico(monkeypatch, tmp_path: Path) -> None:
    vault = _montar_vault(tmp_path)
    cofres = _montar_cofres(tmp_path)
    monkeypatch.setattr(seguranca, "contar_daemon_rodando", lambda: 1)
    (cofres / "telegram.json").write_text("nao é json {", encoding="utf-8")

    relatorio = seguranca.executar_verificacao(vault, cofres)

    assert any("telegram.json" in item for item in relatorio.criticos)


def test_daemon_parado_e_atencao_nao_critico(monkeypatch, tmp_path: Path) -> None:
    vault = _montar_vault(tmp_path)
    cofres = _montar_cofres(tmp_path)
    monkeypatch.setattr(seguranca, "contar_daemon_rodando", lambda: 0)

    relatorio = seguranca.executar_verificacao(vault, cofres)

    assert relatorio.status == "⚠️ Atenção"
    assert any("PARADO" in item for item in relatorio.atencoes)


def test_notas_alteradas_fora_de_c04_ignora_zona_autonoma(tmp_path: Path) -> None:
    vault = _montar_vault(tmp_path)
    agora = time.time()
    (vault / "B01 Projetos" / "nota-recente.md").write_text("x", encoding="utf-8")
    (vault / "C04 Claude Obsidian" / "nota-claude.md").write_text("x", encoding="utf-8")

    total = seguranca.notas_alteradas_fora_de_c04(vault, horas=24.0, agora=agora)

    assert total == 1


def test_registrar_log_segue_protocolo(tmp_path: Path) -> None:
    vault = _montar_vault(tmp_path)
    relatorio = seguranca.Relatorio(infos=["Vault: 15/15 pastas raiz"])

    log_path = seguranca.registrar_log(relatorio, vault)

    conteudo = log_path.read_text(encoding="utf-8")
    assert "Verificação Diária" in conteudo
    assert "Status geral: ✅ OK" in conteudo
    assert "Itens com problema: nenhum" in conteudo


def test_montar_card_destaca_problemas() -> None:
    relatorio = seguranca.Relatorio(
        criticos=["Cofre sumiu: brevo.json"],
        atencoes=["Daemon Telegram PARADO (Stella sem ouvidos)"],
        infos=["Vault: 15/15 pastas raiz"],
    )

    card = seguranca.montar_card(relatorio)

    assert card.startswith("🛡 Segurança diária | ❌ Problema")
    assert "🚨 Cofre sumiu: brevo.json" in card
    assert "⚠️ Daemon Telegram PARADO" in card
