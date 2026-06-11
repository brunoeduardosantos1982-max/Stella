from __future__ import annotations

import logging
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Protocol

import httpx

from stella.adapters.llm.base import LLMResponse

logger = logging.getLogger(__name__)

PASTA_GRAVACOES = Path("D:/VortexBrain00/gravacoes")
VAULT_DIR = Path("D:/VortexBrain00/bssurf00")
COFRE_TELEGRAM = Path("D:/VortexBrain00/.secrets/telegram.json")
REUNIOES_DIR = Path("C04 Claude Obsidian/reunioes")
EXTENSOES_AUDIO_VIDEO = {".mp3", ".m4a", ".wav", ".mp4", ".ogg"}


class LLMCompleter(Protocol):
    def complete(self, prompt: str) -> LLMResponse: ...


def _formatar_timestamp(segundos: float) -> str:
    total = max(0, int(segundos))
    minutos, resto = divmod(total, 60)
    return f"[{minutos:02d}:{resto:02d}]"


def _slug_seguro(nome: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._-]+", "-", nome.strip()).strip("-._")
    return slug or "reuniao"


def transcrever(caminho: Path) -> str:
    from faster_whisper import WhisperModel

    model = WhisperModel("small", device="cpu", compute_type="int8")
    segments, _info = model.transcribe(str(caminho), language="pt", vad_filter=True)

    linhas: list[str] = []
    proximo_timestamp = 0.0
    for segment in segments:
        inicio = float(segment.start)
        texto = str(segment.text).strip()
        if not texto:
            continue
        if not linhas or inicio >= proximo_timestamp:
            linhas.append(f"{_formatar_timestamp(inicio)} {texto}")
            proximo_timestamp = inicio + 30.0
        else:
            linhas.append(texto)
    return "\n".join(linhas).strip()


def resumir(transcricao: str, llm: LLMCompleter) -> str:
    prompt = (
        "Voce e a Stella, assistente de consultoria do Bruno. "
        "Resuma a transcricao abaixo em PT-BR, em Markdown, sem usar travessao. "
        "Entregue exatamente estas secoes:\n"
        "## Resumo executivo\n"
        "5 a 8 linhas sobre o contexto, problema e encaminhamento.\n\n"
        "## Decisoes tomadas\n"
        "Lista objetiva das decisoes.\n\n"
        "## Acoes combinadas\n"
        "Quem faz o que, com linguagem direta.\n\n"
        "## Citacoes literais relevantes do cliente\n"
        "3 a 5 citacoes curtas, preservando as palavras do cliente.\n\n"
        "Transcricao:\n"
        f"{transcricao}"
    )
    return llm.complete(prompt).texto


def salvar_no_vault(nome_base: str, transcricao: str, resumo: str, vault_dir: Path) -> Path:
    agora = datetime.now()
    destino_dir = vault_dir / REUNIOES_DIR
    destino_dir.mkdir(parents=True, exist_ok=True)
    nota_path = destino_dir / f"{agora:%Y-%m-%d}-{_slug_seguro(nome_base)}.md"
    conteudo = (
        "---\n"
        "tipo: reuniao\n"
        "origem: gravador\n"
        f"criado-em: {agora.isoformat(timespec='seconds')}\n"
        "---\n\n"
        "## Resumo\n\n"
        f"{resumo.strip()}\n\n"
        "## Transcrição completa\n\n"
        f"{transcricao.strip()}\n"
    )
    nota_path.write_text(conteudo, encoding="utf-8")
    return nota_path


def avisar_telegram(resumo: str, nota_path: Path, cofre_path: Path) -> None:
    try:
        import json

        cofre = json.loads(cofre_path.read_text(encoding="utf-8"))
        token = str(cofre["bot_token"])
        chat_id = str(cofre["chat_id"])
        resumo_curto = resumo.strip()[:3500]
        texto = f"<b>🎙 Reunião transcrita</b>\n\n{resumo_curto}\n\nNota: {nota_path.name}"
        response = httpx.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": texto, "parse_mode": "HTML"},
            timeout=20,
        )
        response.raise_for_status()
    except Exception as exc:
        logger.warning("Falha ao avisar Telegram sobre nota %s: %s", nota_path.name, exc)


def _arquivos_processaveis(pasta: Path) -> list[Path]:
    pasta.mkdir(parents=True, exist_ok=True)
    return sorted(
        arquivo
        for arquivo in pasta.iterdir()
        if arquivo.is_file()
        and arquivo.suffix.lower() in EXTENSOES_AUDIO_VIDEO
        and not arquivo.with_name(f"{arquivo.name}.feito").exists()
    )


def processar_pasta(pasta: Path, vault_dir: Path, cofre_path: Path, llm: LLMCompleter) -> int:
    processados = 0
    for arquivo in _arquivos_processaveis(pasta):
        try:
            logger.info("Processando gravacao %s", arquivo.name)
            transcricao = transcrever(arquivo)
            resumo = resumir(transcricao, llm)
            nota_path = salvar_no_vault(arquivo.stem, transcricao, resumo, vault_dir)
            avisar_telegram(resumo, nota_path, cofre_path)
            arquivo.with_name(f"{arquivo.name}.feito").touch()
            processados += 1
        except Exception as exc:
            logger.exception("Falha ao processar gravacao %s: %s", arquivo.name, exc)
    return processados


def vigiar_pasta(
    pasta: Path,
    vault_dir: Path,
    cofre_path: Path,
    llm: LLMCompleter,
    intervalo_s: int = 60,
) -> None:
    pasta.mkdir(parents=True, exist_ok=True)
    while True:
        processar_pasta(pasta, vault_dir, cofre_path, llm)
        time.sleep(intervalo_s)
