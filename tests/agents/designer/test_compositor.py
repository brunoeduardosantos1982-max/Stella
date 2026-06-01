import subprocess

from stella.adapters.render.html_renderer import HtmlRenderer
from stella.agents.designer.compositor import HtmlCompositor
from stella.agents.designer.temas.base import FotoHeroContent
from stella.framework.testing.fakes import FakeVault


def _renderer(png: bytes = b"FINALPNG") -> HtmlRenderer:
    cap = {}

    def run(args: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
        cap["args"] = args
        out = next(a.split("=", 1)[1] for a in args if a.startswith("--screenshot="))
        open(out, "wb").write(png)
        return subprocess.CompletedProcess(args, 0, "", "")

    r = HtmlRenderer(browser_path="chrome", runner=run)
    r._cap = cap  # type: ignore[attr-defined]
    return r


def test_compor_grava_png_e_devolve_path() -> None:
    vault = FakeVault()
    comp = HtmlCompositor(renderer=_renderer(b"XYZ"), vault=vault)
    c = FotoHeroContent(headline="5 MITOS")
    path = comp.compor("mitos", c, b"HEROBYTES", post_id="2026-06-12-01", idx=0)
    assert path == "C04 Claude Obsidian/outputs/mktmagneto-ia/imagens/2026-06-12-01/hero0.png"
    assert vault.read_binary(path) == b"XYZ"


def test_downscale_reduz_largura() -> None:
    import io

    from PIL import Image

    from stella.agents.designer.compositor import _downscale

    buf = io.BytesIO()
    Image.new("RGB", (1536, 2048), (10, 20, 30)).save(buf, format="PNG")
    out = _downscale(buf.getvalue(), largura=1080)
    assert Image.open(io.BytesIO(out)).width == 1080


def test_downscale_imagem_pequena_intacta() -> None:
    import io

    from PIL import Image

    from stella.agents.designer.compositor import _downscale

    buf = io.BytesIO()
    Image.new("RGB", (800, 1000), (0, 0, 0)).save(buf, format="PNG")
    out = _downscale(buf.getvalue(), largura=1080)
    assert Image.open(io.BytesIO(out)).width == 800
