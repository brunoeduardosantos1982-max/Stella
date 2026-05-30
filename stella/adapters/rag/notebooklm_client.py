"""NotebookLMRAGClient - adapter RAGClient sobre o CLI `notebooklm`.

Implementa `search(query, k)` via `notebooklm ask ... --json` (grounding sobre um
notebook curado) e `auth_check()` refletindo a sessao local (storage_state.json).
Nao usa API key - reaproveita o login interativo do Bruno.
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import Any

from stella.framework.rag import RAGClient


class NotebookLMError(RuntimeError):
    """Falha (nao-auth) ao consultar o NotebookLM via CLI."""


@dataclass
class NotebookLMRAGClient(RAGClient):
    """Cliente RAG que consulta um notebook do NotebookLM via CLI.

    Args:
        notebook_id: id (ou prefixo) do notebook de referencia da marca.
        bin: caminho/nome do executavel `notebooklm` (default: resolvido na PATH).
        timeout_s: timeout (s) por chamada ao CLI.
    """

    notebook_id: str
    bin: str = "notebooklm"
    timeout_s: int = 60

    def auth_check(self) -> bool:
        """True se a sessao esta valida (`notebooklm auth check` sai 0)."""
        try:
            proc = subprocess.run(
                [self.bin, "auth", "check"],
                capture_output=True,
                text=True,
                timeout=self.timeout_s,
            )
        except (OSError, subprocess.TimeoutExpired):
            return False
        return proc.returncode == 0

    def search(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        """Pergunta ao notebook e devolve a resposta ancorada como 1 doc.

        Formato do doc: {"texto": <resposta>, "citacoes": <lista>}.
        Levanta NotebookLMError se o CLI falhar ou a saida nao for JSON.
        """
        try:
            proc = subprocess.run(
                [
                    self.bin,
                    "ask",
                    query,
                    "--notebook",
                    self.notebook_id,
                    "--json",
                    "--timeout",
                    str(self.timeout_s),
                ],
                capture_output=True,
                text=True,
                timeout=self.timeout_s + 30,
            )
        except (OSError, subprocess.TimeoutExpired) as e:
            raise NotebookLMError(f"falha ao chamar `notebooklm ask`: {e}") from e

        if proc.returncode != 0:
            raise NotebookLMError(
                f"`notebooklm ask` saiu com {proc.returncode}: {proc.stderr.strip()}"
            )
        try:
            dados = json.loads(proc.stdout)
        except json.JSONDecodeError as e:
            raise NotebookLMError(f"saida de `notebooklm ask` nao e JSON: {e}") from e

        # Chaves defensivas: o CLI pode usar answer/text e citations/references.
        texto = str(dados.get("answer") or dados.get("text") or "")
        citacoes = dados.get("citations") or dados.get("references") or []
        if not texto:
            return []
        return [{"texto": texto, "citacoes": citacoes}][:k]
