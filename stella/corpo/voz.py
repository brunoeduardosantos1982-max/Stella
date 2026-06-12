from __future__ import annotations

import re
from pathlib import Path

# Francisca e PT-BR puro; a ThalitaMultilingual e mais natural, mas detecta idioma
# frase a frase e escorrega pro espanhol/ingles em respostas tecnicas (Bruno, 2026-06-11).
VOZ_PADRAO = "pt-BR-FranciscaNeural"
LIMITE_FALA = 1500

_RE_BLOCO_CODIGO = re.compile(r"```.*?```", re.DOTALL)
_RE_CODIGO_INLINE = re.compile(r"`[^`]*`")
_RE_URL = re.compile(r"https?://\S+")
_RE_MARKDOWN = re.compile(r"[*_#>|~\[\]]+")
_RE_EMOJI = re.compile(
    "["
    "\U0001f000-\U0001fbff"  # emojis, simbolos e pictogramas
    "\U00002600-\U000027bf"  # simbolos diversos e dingbats
    "\U0000fe00-\U0000fe0f"  # seletores de variacao
    "\U00002190-\U000021ff"  # setas
    "\U00002b00-\U00002bff"  # setas e simbolos extras
    "⌚⌛⏰-⏿"
    "]+"
)
_RE_ESPACOS = re.compile(r"[ \t]+")


def limpar_para_fala(texto: str) -> str:
    """Prepara texto de resposta para sintese: sem markdown, emoji, URL ou codigo."""
    limpo = _RE_BLOCO_CODIGO.sub(" trecho de código omitido ", texto)
    limpo = _RE_CODIGO_INLINE.sub(" ", limpo)
    limpo = _RE_URL.sub(" link ", limpo)
    limpo = _RE_EMOJI.sub(" ", limpo)
    limpo = _RE_MARKDOWN.sub(" ", limpo)
    limpo = _RE_ESPACOS.sub(" ", limpo)
    limpo = "\n".join(linha.strip() for linha in limpo.splitlines())
    return re.sub(r"\n{2,}", "\n", limpo).strip()


def encurtar_para_fala(texto: str, limite: int = LIMITE_FALA) -> str:
    """Corta na ultima frase completa antes do limite, avisando que o resto esta no texto."""
    if len(texto) <= limite:
        return texto
    corte = texto[:limite]
    fim_frase = max(corte.rfind(". "), corte.rfind("! "), corte.rfind("? "), corte.rfind("\n"))
    if fim_frase > limite // 3:
        corte = corte[: fim_frase + 1]
    return f"{corte.strip()} O restante está na mensagem de texto, Senhor."


def sintetizar(texto: str, destino: Path, voz: str = VOZ_PADRAO) -> Path:
    """Sintetiza fala em mp3 via edge-tts. Levanta ValueError se nao sobrar nada a falar."""
    import edge_tts

    fala = encurtar_para_fala(limpar_para_fala(texto))
    if not fala:
        raise ValueError("texto vazio apos limpeza, nada a sintetizar")

    destino.parent.mkdir(parents=True, exist_ok=True)
    edge_tts.Communicate(fala, voz).save_sync(str(destino))
    return destino
