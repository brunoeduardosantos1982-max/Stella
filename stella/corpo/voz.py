from __future__ import annotations

import json
import re
from pathlib import Path
from xml.sax.saxutils import escape as _xml_escape

# Francisca e PT-BR puro; a ThalitaMultilingual e mais natural, mas detecta idioma
# frase a frase e escorrega pro espanhol/ingles em respostas tecnicas (Bruno, 2026-06-11).
VOZ_PADRAO = "pt-BR-FranciscaNeural"
LIMITE_FALA = 1500

# Cofres de TTS (prioridade: ElevenLabs > Azure > edge-tts gratuito).
# ElevenLabs = voz mais humana. Formato elevenlabs.json:
#   {"key": "...", "voice_id": "...", "model_id": "eleven_multilingual_v2",
#    "stability": 0.45, "similarity_boost": 0.8, "style": 0.35}
# Azure (alternativa). Formato azure.json:
#   {"key": "...", "region": "brazilsouth", "voz": "pt-BR-FranciscaNeural", "estilo": null}
ELEVEN_COFRE = Path("D:/VortexBrain00/.secrets/elevenlabs.json")
AZURE_COFRE = Path("D:/VortexBrain00/.secrets/azure.json")

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
    return f"{corte.strip()} Resumo o essencial por aqui, Senhor; posso detalhar o resto se quiser."


def _carregar_azure() -> dict[str, object] | None:
    """Le o cofre do Azure se existir e estiver completo; senao None (usa edge)."""
    try:
        if AZURE_COFRE.exists():
            cfg = json.loads(AZURE_COFRE.read_text(encoding="utf-8"))
            if isinstance(cfg, dict) and cfg.get("key") and cfg.get("region"):
                return cfg
    except Exception:
        return None
    return None


def _montar_ssml(fala: str, voz: str, estilo: str | None, rate: str) -> str:
    corpo = f'<prosody rate="{rate}">{_xml_escape(fala)}</prosody>'
    if estilo:
        corpo = f'<mstts:express-as style="{estilo}">{corpo}</mstts:express-as>'
    return (
        '<speak version="1.0" '
        'xmlns="http://www.w3.org/2001/10/synthesis" '
        'xmlns:mstts="https://www.w3.org/2001/mstts" '
        'xml:lang="pt-BR">'
        f'<voice name="{voz}">{corpo}</voice></speak>'
    )


def _sintetizar_azure(fala: str, destino: Path, cfg: dict[str, object]) -> Path:
    """Sintese via Azure Speech (REST). Levanta excecao em falha (chamador faz fallback)."""
    import httpx

    voz = str(cfg.get("voz") or VOZ_PADRAO)
    estilo = cfg.get("estilo")  # ex.: "chat", "calm" — None = sem estilo
    rate = cfg.get("rate") or "-2%"  # leve desaceleracao soa mais natural
    url = f"https://{cfg['region']}.tts.speech.microsoft.com/cognitiveservices/v1"
    headers = {
        "Ocp-Apim-Subscription-Key": str(cfg["key"]),
        "Content-Type": "application/ssml+xml",
        "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3",
        "User-Agent": "stella-voz",
    }
    estilo_texto = str(estilo) if estilo else None
    rate_texto = str(rate)
    ssml = _montar_ssml(fala, voz, estilo_texto, rate_texto).encode("utf-8")
    resp = httpx.post(url, headers=headers, content=ssml, timeout=30)
    resp.raise_for_status()
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(resp.content)
    return destino


def _sintetizar_edge(fala: str, destino: Path, voz: str) -> Path:
    import edge_tts

    destino.parent.mkdir(parents=True, exist_ok=True)
    edge_tts.Communicate(fala, voz).save_sync(str(destino))
    return destino


def _carregar_elevenlabs() -> dict[str, object] | None:
    """Le o cofre do ElevenLabs se existir e tiver a key; senao None."""
    try:
        if ELEVEN_COFRE.exists():
            cfg = json.loads(ELEVEN_COFRE.read_text(encoding="utf-8"))
            if isinstance(cfg, dict) and cfg.get("key"):
                return cfg
    except Exception:
        return None
    return None


def _sintetizar_elevenlabs(fala: str, destino: Path, cfg: dict[str, object]) -> Path:
    """Sintese via ElevenLabs (REST). Levanta excecao em falha (chamador faz fallback)."""
    import httpx

    voice_id = cfg.get("voice_id") or "EXAVITQu4vr4xnSDxMaL"  # "Sarah" (padrao multilingue)
    model_id = cfg.get("model_id") or "eleven_multilingual_v2"
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": str(cfg["key"]),
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }
    body = {
        "text": fala,
        "model_id": model_id,
        "voice_settings": {
            "stability": cfg.get("stability", 0.45),
            "similarity_boost": cfg.get("similarity_boost", 0.8),
            "style": cfg.get("style", 0.35),
            "use_speaker_boost": cfg.get("use_speaker_boost", True),
        },
    }
    resp = httpx.post(
        url,
        headers=headers,
        json=body,
        params={"output_format": "mp3_44100_128"},
        timeout=60,
    )
    resp.raise_for_status()
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(resp.content)
    return destino


def falar_elevenlabs(fala: str, destino: Path) -> Path:
    """Sintetiza `fala` JÁ PRONTA (ex.: com break tags) via ElevenLabs, sem limpeza.
    Levanta RuntimeError se o cofre não estiver configurado."""
    cfg = _carregar_elevenlabs()
    if not cfg:
        raise RuntimeError("ElevenLabs não configurado (.secrets/elevenlabs.json)")
    destino.parent.mkdir(parents=True, exist_ok=True)
    return _sintetizar_elevenlabs(fala, destino, cfg)


def sintetizar(texto: str, destino: Path, voz: str = VOZ_PADRAO) -> Path:
    """Sintetiza fala em audio. Prioridade: ElevenLabs > Azure > edge-tts.
    Cada backend, se falhar, cai no proximo. ValueError se nada a falar."""
    fala = encurtar_para_fala(limpar_para_fala(texto))
    if not fala:
        raise ValueError("texto vazio apos limpeza, nada a sintetizar")

    eleven = _carregar_elevenlabs()
    if eleven:
        try:
            return _sintetizar_elevenlabs(fala, destino, eleven)
        except Exception:
            pass  # fallback para Azure/edge

    azure = _carregar_azure()
    if azure:
        try:
            return _sintetizar_azure(fala, destino, azure)
        except Exception:
            pass  # fallback para edge

    return _sintetizar_edge(fala, destino, voz)
