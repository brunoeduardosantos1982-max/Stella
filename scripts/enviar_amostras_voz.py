"""Gera amostras de voz PT-BR e envia ao Telegram do Bruno para escolha da voz da Stella."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import httpx

from stella.corpo.voz import sintetizar

COFRE = Path("D:/VortexBrain00/.secrets/telegram.json")
FRASE = (
    "Oi Bruno! Eu sou a Stella, sua assistente pessoal. "
    "A partir de agora, quando você falar comigo por áudio, eu respondo com a minha voz. "
    "Se gostar dessa aqui, é só me avisar."
)
VOZES = [
    ("pt-BR-FranciscaNeural", "Voz 1: Francisca"),
    ("pt-BR-ThalitaMultilingualNeural", "Voz 2: Thalita"),
]


def main() -> None:
    cofre = json.loads(COFRE.read_text(encoding="utf-8"))
    token = str(cofre["bot_token"])
    chat_id = str(cofre["chat_id"])

    with tempfile.TemporaryDirectory() as tmp:
        for voz, legenda in VOZES:
            destino = Path(tmp) / f"{voz}.mp3"
            sintetizar(FRASE, destino, voz=voz)
            with destino.open("rb") as audio:
                resposta = httpx.post(
                    f"https://api.telegram.org/bot{token}/sendVoice",
                    data={"chat_id": chat_id, "caption": legenda},
                    files={"voice": (destino.name, audio, "audio/mpeg")},
                    timeout=60,
                )
            resposta.raise_for_status()
            print(f"enviada: {legenda} ({destino.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
