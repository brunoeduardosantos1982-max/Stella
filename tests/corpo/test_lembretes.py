from __future__ import annotations

from datetime import datetime
from pathlib import Path

from stella.corpo import lembretes


def _agora() -> datetime:
    return datetime(2026, 6, 14, 15, 0, tzinfo=lembretes.FUSO_STELLA)


def test_adicionar_iso_cria_pendente(tmp_path: Path) -> None:
    store = tmp_path / "lembretes.json"

    item = lembretes.adicionar(
        "2026-06-14T16:00:00-03:00",
        "dentista",
        store_path=store,
        agora=_agora(),
    )

    assert item["texto"] == "dentista"
    assert item["status"] == "pendente"
    assert item["quando"] == "2026-06-14T16:00:00-03:00"
    assert lembretes.carregar(store) == [item]


def test_adicionar_hhmm_passado_agenda_para_amanha(tmp_path: Path) -> None:
    store = tmp_path / "lembretes.json"

    item = lembretes.adicionar("14:30", "agua", store_path=store, agora=_agora())

    assert item["quando"] == "2026-06-15T14:30:00-03:00"


def test_listar_apenas_pendentes(tmp_path: Path) -> None:
    store = tmp_path / "lembretes.json"
    pendente = lembretes.adicionar("16:00", "pendente", store_path=store, agora=_agora())
    enviado = lembretes.adicionar("17:00", "enviado", store_path=store, agora=_agora())
    enviado["status"] = "enviado"
    enviado["enviado_em"] = "2026-06-14T17:00:00-03:00"
    lembretes.salvar([pendente, enviado], store)

    assert lembretes.listar(store_path=store) == [pendente]
    assert lembretes.listar(apenas_pendentes=False, store_path=store) == [pendente, enviado]


def test_remover_por_id(tmp_path: Path) -> None:
    store = tmp_path / "lembretes.json"
    item = lembretes.adicionar("16:00", "dentista", store_path=store, agora=_agora())

    assert lembretes.remover(item["id"], store_path=store) is True
    assert lembretes.carregar(store) == []
    assert lembretes.remover(item["id"], store_path=store) is False


def test_disparar_pendentes_idempotente_ignora_futuros(tmp_path: Path) -> None:
    store = tmp_path / "lembretes.json"
    vencido = lembretes.adicionar(
        "2026-06-14T14:00:00-03:00",
        "vencido",
        store_path=store,
        agora=_agora(),
    )
    futuro = lembretes.adicionar(
        "2026-06-14T16:00:00-03:00",
        "futuro",
        store_path=store,
        agora=_agora(),
    )
    enviados: list[str] = []

    disparados = lembretes.disparar_pendentes(_agora(), store_path=store, enviar=enviados.append)

    assert [item["id"] for item in disparados] == [vencido["id"]]
    assert enviados == ["vencido"]
    atuais = lembretes.carregar(store)
    assert atuais[0]["status"] == "enviado"
    assert atuais[0]["enviado_em"] == "2026-06-14T15:00:00-03:00"
    assert atuais[1] == futuro

    segundo_tick = lembretes.disparar_pendentes(_agora(), store_path=store, enviar=enviados.append)

    assert segundo_tick == []
    assert enviados == ["vencido"]


def test_disparar_pendentes_falha_de_um_item_nao_derruba_outros(tmp_path: Path) -> None:
    store = tmp_path / "lembretes.json"
    lembretes.adicionar("2026-06-14T14:00:00-03:00", "falha", store_path=store, agora=_agora())
    ok = lembretes.adicionar("2026-06-14T14:30:00-03:00", "ok", store_path=store, agora=_agora())
    enviados: list[str] = []

    def enviar(texto: str) -> None:
        if texto == "falha":
            raise RuntimeError("sem rede")
        enviados.append(texto)

    disparados = lembretes.disparar_pendentes(_agora(), store_path=store, enviar=enviar)

    assert [item["id"] for item in disparados] == [ok["id"]]
    assert enviados == ["ok"]
    atuais = lembretes.carregar(store)
    assert atuais[0]["status"] == "pendente"
    assert atuais[1]["status"] == "enviado"


def test_notificar_monta_chamada_certa() -> None:
    enviados: list[str] = []

    lembretes.notificar("teste", enviar=enviados.append)

    assert enviados == ["teste"]
