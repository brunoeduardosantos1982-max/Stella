"""NotebookLMRAGClient - adapter RAGClient sobre o CLI `notebooklm`.

Implementa `search(query, k)` via `notebooklm ask ... --json` (grounding sobre
notebooks curados) e `auth_check()` refletindo a sessao local (storage_state.json).
Com `notebook_id` vazio, consulta TODOS os notebooks da conta (descobertos via
`notebooklm list --json`) e mescla as respostas. Nao usa API key - reaproveita
o login interativo do Bruno.
"""

from __future__ import annotations

import json
import subprocess
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

from stella.framework.rag import RAGClient


class NotebookLMError(RuntimeError):
    """Falha (nao-auth) ao consultar o NotebookLM via CLI."""


@dataclass
class NotebookLMRAGClient(RAGClient):
    """Cliente RAG que consulta notebooks do NotebookLM via CLI.

    Args:
        notebook_id: id (ou prefixo) de um notebook especifico; vazio = todos.
        bin: caminho/nome do executavel `notebooklm` (default: resolvido na PATH).
        timeout_s: timeout (s) por chamada ao CLI.
    """

    notebook_id: str = ""
    bin: str = "notebooklm"
    timeout_s: int = 60

    def auth_check(self) -> bool:
        """True se a sessao esta valida (`notebooklm auth check` sai 0)."""
        try:
            proc = self._run([self.bin, "auth", "check"])
        except NotebookLMError:
            return False
        return proc.returncode == 0

    def search(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        """Pergunta aos notebooks e devolve as respostas ancoradas como docs.

        Formato do doc: {"texto": <resposta>, "citacoes": <lista>, "notebook": <id>}.
        Com notebook_id definido, comportamento original (1 notebook, erro propaga).
        Sem notebook_id, consulta todos em paralelo; notebooks que falharem sao
        ignorados desde que ao menos um responda.
        Levanta NotebookLMError se o CLI falhar ou a saida nao for JSON.
        """
        ids = [self.notebook_id] if self.notebook_id else self._listar_notebooks()
        if not ids:
            return []
        if len(ids) == 1:
            return self._perguntar(ids[0], query)[:k]

        docs: list[dict[str, Any]] = []
        erros: list[str] = []
        # ponytail: 1 subprocesso por notebook em paralelo; se a conta passar de
        # ~8 notebooks, revisitar (latencia e rate limit do NotebookLM).
        with ThreadPoolExecutor(max_workers=min(4, len(ids))) as pool:
            futuros = [pool.submit(self._perguntar, nb, query) for nb in ids]
            for fut in futuros:
                try:
                    docs.extend(fut.result())
                except NotebookLMError as e:
                    erros.append(str(e))
        if not docs and erros:
            raise NotebookLMError("; ".join(erros))
        return docs[:k]

    def _listar_notebooks(self) -> list[str]:
        """Ids de todos os notebooks da conta via `notebooklm list --json`."""
        proc = self._run([self.bin, "list", "--json"])
        if proc.returncode != 0:
            raise NotebookLMError(
                f"`notebooklm list` saiu com {proc.returncode}: {proc.stderr.strip()}"
            )
        try:
            dados = json.loads(proc.stdout)
        except json.JSONDecodeError as e:
            raise NotebookLMError(f"saida de `notebooklm list` nao e JSON: {e}") from e
        return [nb["id"] for nb in dados.get("notebooks", []) if nb.get("id")]

    def _perguntar(self, notebook_id: str, query: str) -> list[dict[str, Any]]:
        """Pergunta a UM notebook e devolve a resposta como lista de 0..1 doc."""
        proc = self._run(
            [
                self.bin,
                "ask",
                query,
                "--notebook",
                notebook_id,
                "--json",
                "--timeout",
                str(self.timeout_s),
            ]
        )
        if proc.returncode != 0:
            raise NotebookLMError(
                f"`notebooklm ask` ({notebook_id}) saiu com {proc.returncode}: "
                f"{proc.stderr.strip()}"
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
        return [{"texto": texto, "citacoes": citacoes, "notebook": notebook_id}]

    def _run(self, cmd: list[str]) -> subprocess.CompletedProcess[str]:
        """subprocess.run com encoding UTF-8 fixo (Windows) e timeout padrao."""
        try:
            return subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=self.timeout_s + 30,
            )
        except (OSError, subprocess.TimeoutExpired) as e:
            raise NotebookLMError(f"falha ao chamar `{' '.join(cmd[:2])}`: {e}") from e
