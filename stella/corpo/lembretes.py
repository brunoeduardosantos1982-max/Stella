from __future__ import annotations

import json
import tempfile
from collections.abc import Callable
from datetime import datetime, time, timedelta, timezone
from pathlib import Path
from typing import Literal, TypedDict
from uuid import uuid4

from stella.corpo.daemon_telegram import load_secrets, send_message

FUSO_STELLA = timezone(timedelta(hours=-3))
STORE_PATH = Path("D:/VortexBrain00/.secrets/lembretes.json")

StatusLembrete = Literal["pendente", "enviado"]
Enviar = Callable[[str], None]


class Lembrete(TypedDict):
    id: str
    quando: str
    texto: str
    status: StatusLembrete
    criado: str
    enviado_em: str | None


def agora_stella() -> datetime:
    return datetime.now(FUSO_STELLA)


def _normalizar_datetime(valor: datetime) -> datetime:
    if valor.tzinfo is None:
        return valor.replace(tzinfo=FUSO_STELLA)
    return valor.astimezone(FUSO_STELLA)


def _parse_quando(quando: str, agora: datetime | None = None) -> datetime:
    referencia = _normalizar_datetime(agora or agora_stella())
    valor = quando.strip()
    try:
        hora = time.fromisoformat(valor)
    except ValueError:
        try:
            return _normalizar_datetime(datetime.fromisoformat(valor))
        except ValueError as exc:
            raise ValueError("quando deve ser ISO ou HH:MM") from exc

    agendado = datetime.combine(referencia.date(), hora, tzinfo=FUSO_STELLA)
    if agendado <= referencia:
        agendado += timedelta(days=1)
    return agendado


def _coagir_lembrete(raw: object) -> Lembrete | None:
    if not isinstance(raw, dict):
        return None
    status = raw.get("status")
    if status not in ("pendente", "enviado"):
        return None
    enviado_em = raw.get("enviado_em")
    return {
        "id": str(raw.get("id", "")),
        "quando": str(raw.get("quando", "")),
        "texto": str(raw.get("texto", "")),
        "status": status,
        "criado": str(raw.get("criado", "")),
        "enviado_em": str(enviado_em) if enviado_em is not None else None,
    }


def carregar(store_path: Path = STORE_PATH) -> list[Lembrete]:
    if not store_path.exists():
        return []
    data = json.loads(store_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        return []
    lembretes: list[Lembrete] = []
    for item in data:
        lembrete = _coagir_lembrete(item)
        if lembrete is not None:
            lembretes.append(lembrete)
    return lembretes


def salvar(lembretes: list[Lembrete], store_path: Path = STORE_PATH) -> None:
    store_path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(lembretes, ensure_ascii=False, indent=2)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=store_path.parent,
        delete=False,
        prefix=f".{store_path.name}.",
        suffix=".tmp",
    ) as tmp:
        tmp.write(payload)
        tmp.write("\n")
        tmp_path = Path(tmp.name)
    tmp_path.replace(store_path)


def adicionar(
    quando: str,
    texto: str,
    *,
    store_path: Path = STORE_PATH,
    agora: datetime | None = None,
) -> Lembrete:
    criado = _normalizar_datetime(agora or agora_stella())
    lembrete: Lembrete = {
        "id": str(uuid4()),
        "quando": _parse_quando(quando, criado).isoformat(timespec="seconds"),
        "texto": texto,
        "status": "pendente",
        "criado": criado.isoformat(timespec="seconds"),
        "enviado_em": None,
    }
    lembretes = carregar(store_path)
    lembretes.append(lembrete)
    salvar(lembretes, store_path)
    return lembrete


def listar(apenas_pendentes: bool = True, *, store_path: Path = STORE_PATH) -> list[Lembrete]:
    lembretes = carregar(store_path)
    if apenas_pendentes:
        return [item for item in lembretes if item["status"] == "pendente"]
    return lembretes


def remover(id: str, *, store_path: Path = STORE_PATH) -> bool:
    lembretes = carregar(store_path)
    filtrados = [item for item in lembretes if item["id"] != id]
    if len(filtrados) == len(lembretes):
        return False
    salvar(filtrados, store_path)
    return True


def _enviar_telegram(texto: str) -> None:
    secrets = load_secrets()
    send_message(secrets.bot_token, secrets.chat_id, texto)


def disparar_pendentes(
    agora: datetime | None = None,
    *,
    store_path: Path = STORE_PATH,
    enviar: Enviar = _enviar_telegram,
) -> list[Lembrete]:
    referencia = _normalizar_datetime(agora or agora_stella())
    lembretes = carregar(store_path)
    enviados: list[Lembrete] = []
    mudou = False

    for lembrete in lembretes:
        if lembrete["status"] != "pendente":
            continue
        quando = _normalizar_datetime(datetime.fromisoformat(lembrete["quando"]))
        if quando > referencia:
            continue
        try:
            enviar(lembrete["texto"])
        except Exception:
            continue
        lembrete["status"] = "enviado"
        lembrete["enviado_em"] = referencia.isoformat(timespec="seconds")
        enviados.append(lembrete)
        mudou = True

    if mudou:
        salvar(lembretes, store_path)
    return enviados


def notificar(texto: str, *, enviar: Enviar = _enviar_telegram) -> None:
    enviar(texto)
