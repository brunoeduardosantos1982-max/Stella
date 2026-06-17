from __future__ import annotations

import re
from pathlib import Path

from stella.corpo import voz

# ElevenLabs limita cada <break> a ~3s; encadeamos para pausas maiores.
_RE_FIM_FRASE = re.compile(r"[.!?]+|\n+")
_BREAK_MAX_SEG = 3.0

# Rótulos de produção e rubricas que NÃO podem ir pro áudio de gravação.
_RE_ROTULO = re.compile(
    r"^\s*[-*•>\d.\)\s]*\*{0,2}_{0,2}"
    r"(g[ae]ncho|hook|cta|call[\s-]*to[\s-]*action|desenvolvimento|abertura|"
    r"virada|fechamento|conclus[ãa]o|cena\s*\d*|narra[çc][ãa]o|legenda|"
    r"hashtags?|roteiro|texto\s+falado|fala)"
    r"\*{0,2}_{0,2}\s*(?:\(\s*\d+\s*[-–a]?\s*\d*\s*s\w*\s*\))?\s*[:\-–]\s*",
    re.IGNORECASE,
)
_RE_DIRECAO_LINHA = re.compile(r"^\s*[\[(].*[\])]\s*$")
_RE_COLCHETE_INLINE = re.compile(r"\[[^\]]*\]")
_RE_HASHTAG = re.compile(r"#\S+")


def dividir_frases(texto: str) -> list[str]:
    """Divide o texto em frases para leitura pausada."""
    return [frase.strip() for frase in _RE_FIM_FRASE.split(texto) if frase.strip()]


def limpar_para_gravacao(texto: str) -> str:
    """Tira rótulos (Gancho, CTA, ...) e rubricas, deixando só a fala a ser gravada."""
    falas: list[str] = []
    for linha in texto.splitlines():
        if _RE_DIRECAO_LINHA.match(linha):
            continue
        sem_rotulo = _RE_ROTULO.sub("", linha)
        limpa = _RE_HASHTAG.sub("", _RE_COLCHETE_INLINE.sub("", sem_rotulo)).strip()
        if limpa:
            falas.append(limpa)
    return "\n".join(falas)


def montar_pausa(gap_seg: float) -> str:
    """Tags <break> do ElevenLabs somando gap_seg (encadeia, pois o limite é ~3s)."""
    restante = max(0.0, gap_seg)
    tags: list[str] = []
    while restante > _BREAK_MAX_SEG + 1e-6:
        tags.append(f'<break time="{_BREAK_MAX_SEG:g}s" />')
        restante -= _BREAK_MAX_SEG
    if restante > 1e-6:
        tags.append(f'<break time="{round(restante, 2):g}s" />')
    return " ".join(tags)


def montar_fala(texto: str, gap_seg: float) -> str:
    """Frases limpas, unidas pelas pausas <break>. ValueError se nada sobrar.

    Tira rótulos/rubricas de produção antes (rede de segurança: o áudio é só fala).
    """
    texto = limpar_para_gravacao(texto)
    frases = [voz.limpar_para_fala(frase) for frase in dividir_frases(texto)]
    frases = [frase for frase in frases if frase]
    if not frases:
        raise ValueError("texto vazio, nada a sintetizar")
    pausa = montar_pausa(gap_seg)
    separador = f" {pausa} " if pausa else " "
    return separador.join(frases)


def gerar(texto: str, destino: Path, *, gap_seg: float = 5.0) -> Path:
    """Gera um MP3 ear-prompter: frases com pausas de ~gap_seg entre elas.

    Usa as break tags nativas do ElevenLabs (sem pydub/ffmpeg). Requer o
    cofre `.secrets/elevenlabs.json` configurado.
    """
    if gap_seg < 0:
        raise ValueError("gap_seg deve ser maior ou igual a zero")
    fala = montar_fala(texto, gap_seg)
    destino.parent.mkdir(parents=True, exist_ok=True)
    return voz.falar_elevenlabs(fala, destino)
