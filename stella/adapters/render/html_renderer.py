"""HtmlRenderer - renderiza HTML em PNG via Chrome/Edge headless."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from collections.abc import Callable
from dataclasses import dataclass, field

from stella.adapters.render.base import RenderError

Runner = Callable[[list[str], int], subprocess.CompletedProcess[str]]

_CANDIDATOS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]


def _default_runner(args: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout)


def _achar_browser() -> str | None:
    for nome in ("chrome", "chrome.exe", "msedge", "msedge.exe"):
        p = shutil.which(nome)
        if p:
            return p
    for candidato in _CANDIDATOS:
        if os.path.exists(candidato):
            return candidato
    return None


@dataclass
class HtmlRenderer:
    browser_path: str | None = None
    runner: Runner = field(default=_default_runner)
    timeout_s: int = 60

    def render(self, html: str, *, width: int = 1080, height: int = 1350) -> bytes:
        browser = self.browser_path or _achar_browser()
        if not browser:
            raise RenderError(
                "Navegador não encontrado. Instale Chrome/Edge ou defina "
                "STELLA_RENDER_BROWSER_PATH."
            )
        with tempfile.TemporaryDirectory() as tmp:
            page = os.path.join(tmp, "page.html")
            out = os.path.join(tmp, "out.png")
            with open(page, "w", encoding="utf-8") as f:
                f.write(html)
            args = [
                browser,
                "--headless=new",
                "--disable-gpu",
                "--hide-scrollbars",
                "--allow-file-access-from-files",
                "--force-device-scale-factor=1",
                f"--window-size={width},{height}",
                "--virtual-time-budget=12000",
                f"--screenshot={out}",
                "file://" + page.replace("\\", "/"),
            ]
            try:
                proc = self.runner(args, self.timeout_s)
            except FileNotFoundError as e:
                raise RenderError(f"Navegador não encontrado em {browser!r}.") from e
            except subprocess.TimeoutExpired as e:
                raise RenderError(f"Render excedeu {self.timeout_s}s.") from e
            if proc.returncode != 0:
                raise RenderError(
                    f"Render falhou (exit {proc.returncode}): {(proc.stderr or '').strip()}"
                )
            if not os.path.exists(out):
                raise RenderError("Render não gerou o PNG.")
            with open(out, "rb") as f:
                return f.read()
