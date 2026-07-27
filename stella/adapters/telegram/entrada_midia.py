"""Recebe vídeo, foto e documento pelo Telegram e guarda em `_entrada-midia/`.

Por que existe: o Bruno grava Reel e Story no celular, e o caminho natural dele
para mandar qualquer coisa é o Telegram da Stella. Antes disto o daemon só
baixava áudio, para transcrever; qualquer outra mídia era ignorada em silêncio.

Limite herdado da Meta, que NÃO dá para contornar aqui: um bot do Telegram só
baixa arquivo de até 20 MB pelo `getFile`. Vídeo enviado como **documento**
mantém o tamanho original e costuma estourar; enviado como **vídeo**, o
Telegram comprime e quase sempre cabe. Por isso o erro de arquivo grande é
tratado com uma resposta que ENSINA o caminho, em vez de só falhar.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx

PASTA_ENTRADA = Path("D:/VortexBrain00/_entrada-midia")

# Fuso de Brasília sem ZoneInfo: no Windows a base tz pode não existir.
BRASILIA = timezone(timedelta(hours=-3))


def _sem_acento(texto: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn"
    )


def apelidar(texto: str) -> str:
    """'Praia de Maceió!' -> 'praia-de-maceio'. Vazio vira string vazia."""
    limpo = _sem_acento(texto).lower()
    limpo = re.sub(r"[^a-z0-9]+", "-", limpo).strip("-")
    return limpo[:60]


# Pistas de que o arquivo é uma OFERTA de fornecedor, não peça de post.
# Inclui os nomes dos fornecedores porque é comum a legenda ser só isso.
PISTAS_DE_OFERTA = (
    "oferta",
    "lamina",
    "pacote",
    "tarifario",
    "bloqueio",
    "incomum",
    "brt",
    "tt operadora",
    "cativa",
    "ehtl",
)


def escolher_pasta(legenda: str) -> str:
    """A legenda roteia. Sem pista, cai em reels, que é o volume.

    Oferta vem antes de story: uma lâmina legendada "oferta para story" é uma
    oferta, e o destino dela é a curadoria, não a pasta de peças prontas. O que
    vira Story é decidido DEPOIS de o preço e o roteiro serem conferidos.
    """
    alvo = _sem_acento(legenda).lower()
    if any(pista in alvo for pista in PISTAS_DE_OFERTA):
        return "ofertas"
    if "story" in alvo or "stories" in alvo:
        return "stories"
    return "reels"


def extrair_midia(message: dict[str, Any]) -> dict[str, Any] | None:
    """Devolve {file_id, nome, tamanho} da mídia da mensagem, ou None.

    Áudio e voz ficam de fora de propósito: quem cuida deles é a transcrição.
    """
    video = message.get("video")
    if isinstance(video, dict) and video.get("file_id"):
        return {
            "file_id": video["file_id"],
            "nome": str(video.get("file_name") or "video.mp4"),
            "tamanho": int(video.get("file_size") or 0),
        }

    animacao = message.get("animation")
    if isinstance(animacao, dict) and animacao.get("file_id"):
        return {
            "file_id": animacao["file_id"],
            "nome": str(animacao.get("file_name") or "animacao.mp4"),
            "tamanho": int(animacao.get("file_size") or 0),
        }

    documento = message.get("document")
    if isinstance(documento, dict) and documento.get("file_id"):
        return {
            "file_id": documento["file_id"],
            "nome": str(documento.get("file_name") or "arquivo"),
            "tamanho": int(documento.get("file_size") or 0),
        }

    # Foto vem como lista de tamanhos, do menor ao maior. Queremos o maior.
    fotos = message.get("photo")
    if isinstance(fotos, list) and fotos:
        maior = fotos[-1]
        if isinstance(maior, dict) and maior.get("file_id"):
            return {
                "file_id": maior["file_id"],
                "nome": "foto.jpg",
                "tamanho": int(maior.get("file_size") or 0),
            }

    return None


def montar_nome(legenda: str, nome_original: str, agora: datetime | None = None) -> str:
    """Nome final: data + apelido da legenda + extensão original.

    A data na frente faz a pasta se ordenar sozinha, e evita que dois vídeos
    com a mesma legenda se sobrescrevam.
    """
    quando = (agora or datetime.now(BRASILIA)).strftime("%Y-%m-%d-%H%M")
    sufixo = Path(nome_original).suffix or ".mp4"
    apelido = apelidar(legenda) or "sem-legenda"
    return f"{quando}__{apelido}{sufixo}"


def caminho_livre(destino: Path) -> Path:
    """Devolve um caminho que ainda não existe, somando -2, -3... se preciso.

    O nome tem precisão de MINUTO. Quando o Bruno manda vários vídeos seguidos
    sem legenda, todos viram `...__sem-legenda.mp4` no mesmo minuto e o
    download seguinte sobrescreve o anterior em silêncio. Aconteceu de verdade
    em 2026-07-27: 9 arquivos chegaram, 7 sobraram. Daí esta guarda existir, e
    daí ela ter teste próprio.
    """
    if not destino.exists():
        return destino
    for n in range(2, 1000):
        candidato = destino.with_name(f"{destino.stem}-{n}{destino.suffix}")
        if not candidato.exists():
            return candidato
    raise ValueError(f"não achei nome livre para {destino}")


class ArquivoGrandeDemais(Exception):
    """O Telegram recusou o download por tamanho."""


def baixar(
    token: str,
    file_id: str,
    destino: Path,
    *,
    http_get: Callable[..., Any] = httpx.get,
) -> Path:
    info = http_get(
        f"https://api.telegram.org/bot{token}/getFile",
        params={"file_id": file_id},
        timeout=30,
    )
    dados = info.json() if callable(getattr(info, "json", None)) else {}
    if not dados.get("ok", False):
        descricao = str(dados.get("description", "")).lower()
        if "too big" in descricao or "file is too big" in descricao:
            raise ArquivoGrandeDemais(descricao)
        raise ValueError(f"getFile falhou: {dados.get('description', 'motivo desconhecido')}")

    caminho_remoto = str((dados.get("result") or {}).get("file_path", ""))
    if not caminho_remoto:
        raise ValueError("getFile sem file_path na resposta")

    conteudo = http_get(f"https://api.telegram.org/file/bot{token}/{caminho_remoto}", timeout=300)
    conteudo.raise_for_status()
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(conteudo.content)
    return destino


def guardar(
    message: dict[str, Any],
    token: str,
    *,
    raiz: Path = PASTA_ENTRADA,
    http_get: Callable[..., Any] = httpx.get,
    agora: datetime | None = None,
) -> tuple[Path, str] | None:
    """Salva a mídia da mensagem e devolve (caminho, pasta). None se não houver.

    Levanta ArquivoGrandeDemais quando o Telegram recusa: quem chama traduz
    isso em uma resposta útil ao Bruno.
    """
    midia = extrair_midia(message)
    if midia is None:
        return None

    legenda = str(message.get("caption") or "")
    pasta = escolher_pasta(legenda)
    nome = montar_nome(legenda, midia["nome"], agora)
    destino = caminho_livre(raiz / pasta / nome)
    baixar(token, midia["file_id"], destino, http_get=http_get)
    _guardar_legenda(destino, legenda, agora)
    return destino, pasta


def _guardar_legenda(destino: Path, legenda: str, agora: datetime | None) -> None:
    """Grava a legenda inteira ao lado do arquivo.

    O nome do arquivo só carrega um apelido encurtado. Numa oferta, a legenda
    costuma trazer o que decide o uso ("comercial, embarque Navegantes, para
    anúncio") e perder isso obriga a perguntar de novo.
    """
    if not legenda.strip():
        return
    quando = (agora or datetime.now(BRASILIA)).strftime("%Y-%m-%d %H:%M")
    destino.with_suffix(destino.suffix + ".txt").write_text(
        f"{quando}\n\n{legenda.strip()}\n", encoding="utf-8"
    )
