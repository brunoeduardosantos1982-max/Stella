import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from stella.adapters.llm.base import LLMProvider
from stella.adapters.vault.base import VaultRepository
from stella.usecases.base import EntradaInvalida

_PROMPT_EXTRACAO = (
    "Você está ajudando a capturar uma ideia rápida no vault Obsidian do Bruno.\n"
    "Receberá uma ideia em texto livre e deve devolver APENAS um JSON com:\n"
    '  - "titulo": string curta (3-8 palavras) que descreve a ideia\n'
    '  - "tags": lista de 1-3 strings, cada uma uma tag relevante (ex: "marketing", "tecnico", "ideia")\n'
    "Responda SOMENTE o JSON, sem cercas de código, sem explicações.\n\n"
    "Ideia:\n{texto}"
)

_PASTA_INBOX = "A00 Inbox"


@dataclass
class EntradaCaptura:
    texto: str
    momento: datetime


@dataclass
class ResultadoCaptura:
    path: str
    titulo: str
    tags: list[str]


class CapturarIdeia:
    """Capacidade 1 — captura texto livre como nota em A00 Inbox."""

    def __init__(self, llm: LLMProvider, vault_repo: VaultRepository) -> None:
        self._llm = llm
        self._vault = vault_repo

    def execute(self, entrada: EntradaCaptura) -> ResultadoCaptura:
        texto = entrada.texto.strip()
        if not texto:
            raise EntradaInvalida("texto da ideia não pode ser vazio")

        meta = self._extrair_meta(texto)
        path = self._gerar_path(entrada.momento, meta["titulo"])
        frontmatter: dict[str, Any] = {
            "title": meta["titulo"],
            "tipo": "ideia",
            "criado-em": entrada.momento.strftime("%Y-%m-%dT%H:%M:%S"),
            "tags": meta["tags"],
        }
        self._vault.write_note(path, content=texto, frontmatter=frontmatter)
        return ResultadoCaptura(path=path, titulo=meta["titulo"], tags=meta["tags"])

    def _extrair_meta(self, texto: str) -> dict[str, Any]:
        prompt = _PROMPT_EXTRACAO.replace("{texto}", texto)
        resp = self._llm.complete(prompt)
        try:
            dados = json.loads(resp.texto)
            titulo = str(dados.get("titulo", "")).strip()
            tags = [str(t).strip() for t in dados.get("tags", [])]
            if not titulo:
                raise ValueError("titulo vazio")
            return {"titulo": titulo, "tags": tags}
        except (json.JSONDecodeError, ValueError):
            return {"titulo": self._fallback_titulo(texto), "tags": []}

    @staticmethod
    def _fallback_titulo(texto: str) -> str:
        palavras = texto.split()[:6]
        return " ".join(palavras).capitalize()

    @staticmethod
    def _gerar_path(momento: datetime, titulo: str) -> str:
        timestamp = momento.strftime("%Y-%m-%d %H-%M")
        slug = re.sub(r"[^\w\s\-—]", "", titulo).strip()[:60]
        return f"{_PASTA_INBOX}/{timestamp} — {slug}.md"
