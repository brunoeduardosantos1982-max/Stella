"""Testes da integração do apelido no radar.py (ItemRadar, aplicar_apelidos, card)."""

from datetime import datetime

from stella.corpo import radar


def test_aplicar_apelidos_slug_e_unico_no_lote():
    itens = [
        radar.ItemRadar("T1", "u1", "v", "r", "g", apelido="IA Google Agentes"),
        radar.ItemRadar("T2", "u2", "v", "r", "g", apelido="IA Google Agentes"),
    ]
    radar.aplicar_apelidos(itens, set())
    assert itens[0].apelido == "ia-google-agentes"
    assert itens[1].apelido == "ia-google-agentes-2"


def test_aplicar_apelidos_fallback_para_titulo_quando_vazio():
    itens = [radar.ItemRadar("Meu Título Massa", "u", "v", "r", "g")]
    radar.aplicar_apelidos(itens, set())
    assert itens[0].apelido == "meu-titulo-massa"


def test_aplicar_apelidos_evita_colidir_com_existentes():
    itens = [radar.ItemRadar("T", "u", "v", "r", "g", apelido="ja-existe")]
    radar.aplicar_apelidos(itens, {"ja-existe"})
    assert itens[0].apelido == "ja-existe-2"


def test_montar_card_mostra_apelido_quando_presente():
    it = radar.ItemRadar(
        "Título", "https://x.com/a", "x.com", "resumo", "gancho", apelido="ia-google-agentes"
    )
    card = radar.montar_card([it], "14h", agora=datetime(2026, 6, 24, 14, 0, tzinfo=radar.FUSO))
    assert "ia-google-agentes" in card
