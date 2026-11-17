"""Roteamento de geradores de conteúdo do Telegram.

O modo conteúdo genérico do daemon (`PERSONA_CONTEUDO`) é do @brunoe.santos: roda em
Opus, com fluxo de 3 etapas e saída em `outputs/conteudo/<nicho>`. Como ele dispara por
palavras soltas (script, roteiro, reel, pauta, conteúdo), qualquer pedido de outro canal
caía nele e herdava persona, sessão e pasta de saída erradas (2026-09-28).

Regra: cada gerador é identificado pelo nome, tem dono e contexto próprios e NÃO passa
pelo `claude -p` do chat nem toca em `SESSION_STATE` ou `CONTEUDO_STATE`. O roteamento
acontece ANTES do modo conteúdo genérico.

Geradores hoje:
- brujosie: canal @brujosie.preparados. Dispara `pipeline/rotina-pauta.ps1 -Tema ...`,
  que pesquisa, escreve roteiro e copy em `pautas/` e avisa no Telegram. Não gera mídia
  nem publica.
"""

from __future__ import annotations

import re
import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

BRUJOSIE_SCRIPT = Path(
    "D:/VortexBrain00/bssurf00/B01 Projetos/brujosie-preparados/pipeline/rotina-pauta.ps1"
)
TEMA_MAX = 200

_RE_BRUJOSIE = re.compile(r"(?<!\w)@?bru\s?josie(?:[\s.]?preparados)?(?!\w)", re.IGNORECASE)
_RE_DATA_NUM = re.compile(r"(?<!\d)(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?(?!\d)")
_RE_DEPOIS_AMANHA = re.compile(r"\bdepois\s+de\s+amanh[ãa]\b", re.IGNORECASE)
_RE_AMANHA = re.compile(r"\bamanh[ãa]\b", re.IGNORECASE)
_RE_HOJE = re.compile(r"\bhoje\b", re.IGNORECASE)
# Palavras de enfeite no começo do pedido ("pauta brujosie: tema engasgo"), que não são o tema.
_RE_ENFEITE = re.compile(
    r"^(?:[\s:;,.\-–—]+|stella|pauta|tema|sobre|para|pra|pro|de|do|da|o|a|um|uma|"
    r"epis[oó]dio|ep\.?\s*\d*|novo|nova|cri[ae]r?|fa[çz]a|fazer|quero|preciso|"
    r"gera(?:r)?|me|manda|por\s+favor)(?![\wÀ-ÿ])",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class PedidoPauta:
    tema: str | None
    data: str | None  # AAAA-MM-DD, ou None (a rotina assume amanhã)


def rotear_gerador(texto: str) -> str | None:
    """Nome do gerador que reclama a mensagem, ou None (segue o fluxo normal do daemon)."""
    if _RE_BRUJOSIE.search(texto):
        return "brujosie"
    return None


def _data_do_texto(texto: str, hoje: date) -> tuple[date | None, str]:
    """Extrai a data pedida e devolve o texto sem ela."""
    if _RE_DEPOIS_AMANHA.search(texto):
        return hoje + timedelta(days=2), _RE_DEPOIS_AMANHA.sub(" ", texto)
    if _RE_AMANHA.search(texto):
        return hoje + timedelta(days=1), _RE_AMANHA.sub(" ", texto)
    if _RE_HOJE.search(texto):
        return hoje, _RE_HOJE.sub(" ", texto)
    m = _RE_DATA_NUM.search(texto)
    if m:
        dia, mes = int(m.group(1)), int(m.group(2))
        ano = int(m.group(3)) if m.group(3) else hoje.year
        if ano < 100:
            ano += 2000
        try:
            return date(ano, mes, dia), texto[: m.start()] + " " + texto[m.end() :]
        except ValueError:
            return None, texto
    return None, texto


def interpretar_pedido_brujosie(texto: str, *, hoje: date | None = None) -> PedidoPauta:
    hoje = hoje or datetime.now().date()
    sem_marca = _RE_BRUJOSIE.sub(" ", texto)
    alvo, resto = _data_do_texto(sem_marca, hoje)
    resto = resto.strip()
    # tira o comando "/" solto que sobra de "/brujosie ..." e os enfeites do começo
    resto = re.sub(r"^/+", "", resto).strip()
    while True:
        novo = _RE_ENFEITE.sub("", resto, count=1).lstrip()
        if novo == resto:
            break
        resto = novo
    tema = re.sub(r"\s+", " ", resto).strip(" \t\n\r:;,.-–—\"'")
    tema = tema.lstrip("-").strip()[:TEMA_MAX]
    return PedidoPauta(tema=tema or None, data=alvo.isoformat() if alvo else None)


def _popen_oculto(args: list[str]) -> subprocess.Popen[bytes]:
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) | getattr(
        subprocess, "CREATE_NEW_PROCESS_GROUP", 0
    )
    return subprocess.Popen(  # noqa: S603 - argumentos em lista, sem shell
        args,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=flags,
    )


def _data_br(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d:%d/%m}"


def responder_brujosie(
    texto: str,
    *,
    popen: Callable[[list[str]], object] = _popen_oculto,
    script: Path = BRUJOSIE_SCRIPT,
    hoje: date | None = None,
) -> str:
    """Interpreta o pedido, dispara a rotina em segundo plano e devolve a resposta do chat."""
    pedido = interpretar_pedido_brujosie(texto, hoje=hoje)
    if not pedido.tema:
        return (
            "Senhor, pauta do brujosie precisa de um tema. "
            "Mande, por exemplo: brujosie engasgo, ou brujosie afogamento dia 02/10."
        )
    if not script.exists():
        return "Senhor, não achei a rotina de pauta do brujosie. Ela não foi disparada."
    args = [
        "powershell.exe",
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
        "-Tema",
        pedido.tema,
    ]
    if pedido.data:
        args += ["-Data", pedido.data]
    popen(args)
    quando = f" para {_data_br(pedido.data)}" if pedido.data else " para amanhã"
    return (
        f"Senhor, pauta do brujosie sobre {pedido.tema}{quando} em preparo. "
        "Levo alguns minutos e aviso aqui quando o roteiro e a copy estiverem prontos. "
        "Nada é gerado nem publicado antes da sua aprovação."
    )


def responder_gerador(nome: str, texto: str) -> str:
    if nome == "brujosie":
        return responder_brujosie(texto)
    raise ValueError(f"gerador desconhecido: {nome}")
