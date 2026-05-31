"""CliHiggsFieldClient — gera imagens via o binário oficial `hf` (Higgsfield CLI).

Modelo: text2image_soul_v2 (Higgsfield Soul V2). A autenticação é gerenciada
pelo próprio `hf` (token salvo via `hf auth login`); este cliente não passa token.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from collections.abc import Callable

from stella.adapters.higgsfield.base import HiggsFieldError

_MODEL = "text2image_soul_v2"
_DEFAULT_ASPECT = "1:1"
_DEFAULT_QUALITY = "2k"
_VALID_ASPECTS = {"1:1", "16:9", "9:16", "4:3", "3:4", "3:2", "2:3"}
_VALID_QUALITIES = {"1.5k", "2k"}
_TIMEOUT_S = 300

_URL_RE = re.compile(
    r"https?://[^\s\"'<>?]+\.(?:jpg|jpeg|png|webp)(?:\?[^\s\"'<>]*)?",
    re.IGNORECASE,
)

Runner = Callable[[list[str], int], "subprocess.CompletedProcess[str]"]


def _default_runner(args: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout)


class CliHiggsFieldClient:
    """Cliente que faz subprocess para `hf generate create text2image_soul_v2`.

    Args:
        hf_path: caminho do binário `hf` (default: resolvido via PATH).
        aspect_ratio: um de _VALID_ASPECTS (default "1:1").
        quality: um de _VALID_QUALITIES (default "2k").
        runner: injetável para testes; recebe (args, timeout) e devolve CompletedProcess.
    """

    def __init__(
        self,
        hf_path: str | None = None,
        aspect_ratio: str = _DEFAULT_ASPECT,
        quality: str = _DEFAULT_QUALITY,
        runner: Runner | None = None,
    ) -> None:
        if aspect_ratio not in _VALID_ASPECTS:
            raise HiggsFieldError(
                f"aspect_ratio inválido: {aspect_ratio!r}. Use um de {sorted(_VALID_ASPECTS)}."
            )
        if quality not in _VALID_QUALITIES:
            raise HiggsFieldError(
                f"quality inválida: {quality!r}. Use um de {sorted(_VALID_QUALITIES)}."
            )
        self._hf = hf_path or shutil.which("hf") or "hf"
        self._aspect = aspect_ratio
        self._quality = quality
        self._run = runner or _default_runner

    def generate_image(self, prompt: str, soul_id: str | None = None) -> str:
        args = [
            self._hf,
            "generate",
            "create",
            _MODEL,
            "--prompt",
            prompt,
            "--aspect_ratio",
            self._aspect,
            "--quality",
            self._quality,
            "--wait",
            "--json",
        ]
        # O CLI `hf` aceita o soul_id direto como string e monta o objeto
        # custom_reference_id internamente (validado via `hf generate cost`).
        if soul_id:
            args += ["--custom_reference_id", soul_id]
        try:
            proc = self._run(args, _TIMEOUT_S)
        except FileNotFoundError as e:
            raise HiggsFieldError(
                f"binário `hf` não encontrado em {self._hf!r}. Instale o Higgsfield CLI."
            ) from e
        except subprocess.TimeoutExpired as e:
            raise HiggsFieldError(f"Higgsfield não respondeu a tempo ({_TIMEOUT_S}s).") from e

        if proc.returncode != 0:
            raise HiggsFieldError(
                f"hf falhou (exit {proc.returncode}): {(proc.stderr or proc.stdout).strip()}"
            )
        return self._extrair_url(proc.stdout)

    @staticmethod
    def _extrair_url(stdout: str) -> str:
        match = _URL_RE.search(stdout or "")
        if not match:
            raise HiggsFieldError(
                f"resposta do hf sem URL de imagem: {(stdout or '').strip()[:200]}"
            )
        return match.group(0)
