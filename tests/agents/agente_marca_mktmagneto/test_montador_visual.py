"""Testes do MontadorVisual — HTML do kit → PNG via render injetado."""

from stella.agents.agente_marca_mktmagneto.montador_visual import MontadorVisual
from stella.agents.agente_marca_mktmagneto.redator import PostTexto
from stella.framework.testing.fakes import FakeVault


class _FakePlaywright:
    """Captura o HTML que seria renderizado e devolve bytes determinísticos."""

    def __init__(self) -> None:
        self.html_capturado: str | None = None
        self.width: int = 0
        self.height: int = 0

    def render_png(self, html: str, width: int, height: int) -> bytes:
        self.html_capturado = html
        self.width = width
        self.height = height
        return b"PNGFAKE"


_TEMPLATE_PATH = "C04 Claude Obsidian/outputs/mktmagneto-ia/templates/capa-carrossel.html"


def _post_basico() -> PostTexto:
    return PostTexto(
        pilar=1,
        titulo="Hook impactante",
        legenda="🔥 Hook\n\nctx\n\ncorpo\n\n👇 CTA",
        hashtags=["#a"] * 12,
        slides=["s1", "s2", "s3"],
    )


def test_preenche_template_e_renderiza():
    """O HTML do template ganha o título do post; PNG é devolvido."""
    vault = FakeVault(
        {
            _TEMPLATE_PATH: ("<html><body>{{TITULO}}</body></html>", {}),
        }
    )
    render = _FakePlaywright()
    m = MontadorVisual(vault=vault, render=render)
    png_bytes = m.montar(_post_basico(), post_id="2026-05-26-01")
    assert png_bytes == b"PNGFAKE"
    assert render.html_capturado is not None
    assert "Hook impactante" in render.html_capturado
    assert render.width == 1080
    assert render.height == 1350


def test_template_ausente_levanta_erro_claro():
    """Sem o template no vault, montagem falha com erro descritivo."""
    vault = FakeVault({})  # vazio
    render = _FakePlaywright()
    m = MontadorVisual(vault=vault, render=render)
    import pytest

    with pytest.raises(FileNotFoundError, match="template"):
        m.montar(_post_basico(), post_id="2026-05-26-01")


def test_legenda_tambem_eh_substituida():
    """Se o template tiver {{LEGENDA}}, é substituída pelo texto da legenda."""
    vault = FakeVault(
        {
            _TEMPLATE_PATH: ("<html><body>{{TITULO}} - {{LEGENDA}}</body></html>", {}),
        }
    )
    render = _FakePlaywright()
    m = MontadorVisual(vault=vault, render=render)
    m.montar(_post_basico(), post_id="x")
    assert "🔥 Hook" in (render.html_capturado or "")


def test_sem_placeholders_template_passa_intacto():
    """Template sem placeholders ainda renderiza (HTML estático)."""
    vault = FakeVault(
        {
            _TEMPLATE_PATH: ("<html><body>OI</body></html>", {}),
        }
    )
    render = _FakePlaywright()
    m = MontadorVisual(vault=vault, render=render)
    png = m.montar(_post_basico(), post_id="x")
    assert png == b"PNGFAKE"
    assert (render.html_capturado or "") == "<html><body>OI</body></html>"
