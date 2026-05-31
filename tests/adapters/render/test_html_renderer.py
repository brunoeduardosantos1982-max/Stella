"""Testes do HtmlRenderer."""

import subprocess

import pytest

from stella.adapters.render.base import RenderError
from stella.adapters.render.html_renderer import HtmlRenderer


def _runner(returncode: int = 0, png: bytes = b"PNGBYTES", stderr: str = ""):
    cap = {}

    def run(args: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
        cap["args"] = args
        out = next(a.split("=", 1)[1] for a in args if a.startswith("--screenshot="))
        if returncode == 0:
            with open(out, "wb") as f:
                f.write(png)
        return subprocess.CompletedProcess(args, returncode, "", stderr)

    run.cap = cap  # type: ignore[attr-defined]
    return run


def test_render_devolve_bytes_do_png() -> None:
    r = HtmlRenderer(browser_path="chrome", runner=_runner(png=b"ABC123"))
    assert r.render("<h1>oi</h1>") == b"ABC123"


def test_render_monta_comando_headless_com_dimensoes() -> None:
    runner = _runner()
    HtmlRenderer(browser_path="chrome", runner=runner).render("<h1>x</h1>", width=1080, height=1350)
    args = runner.cap["args"]  # type: ignore[attr-defined]
    assert args[0] == "chrome"
    assert "--headless=new" in args
    assert "--window-size=1080,1350" in args
    assert any(a.startswith("--screenshot=") for a in args)
    assert any(a.startswith("file://") for a in args)


def test_render_exit_nao_zero_levanta_render_error() -> None:
    r = HtmlRenderer(browser_path="chrome", runner=_runner(returncode=1, stderr="boom"))
    with pytest.raises(RenderError, match="boom"):
        r.render("<h1>x</h1>")


def test_render_browser_ausente_levanta_render_error() -> None:
    def run(args: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError("chrome")

    with pytest.raises(RenderError, match="não encontrado|nao encontrado"):
        HtmlRenderer(browser_path="chrome", runner=run).render("<h1>x</h1>")
