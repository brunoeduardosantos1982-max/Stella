import subprocess

from stella.adapters.render.html_renderer import HtmlRenderer
from stella.agents.designer.resolvedor_tipografico import ResolvedorTipografico
from stella.agents.designer.spec import DesignSpec, SlideSpec
from stella.framework.testing.fakes import FakeVault

_T = "C04 Claude Obsidian/outputs/mktmagneto-ia/templates"
_FILA = "C04 Claude Obsidian/Stella-publicacao/fila"


def _renderer() -> HtmlRenderer:
    cap = {}

    def run(args: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
        del timeout
        page = next(a[7:] for a in args if a.startswith("file://"))
        cap["html"] = open(page, encoding="utf-8").read()
        out = next(a.split("=", 1)[1] for a in args if a.startswith("--screenshot="))
        open(out, "wb").write(b"PNG")
        return subprocess.CompletedProcess(args, 0, "", "")

    r = HtmlRenderer(browser_path="chrome", runner=run)
    r._cap = cap  # type: ignore[attr-defined]
    return r


def _vault_com_template() -> FakeVault:
    v = FakeVault()
    v.write_binary(f"{_T}/slide-conteudo.html", b"<div>{{COUNTER}}|{{TEXTO}}|{{TAG}}</div>")
    v.write_binary(f"{_T}/capa-carrossel.html", b"<div>capa {{HEADLINE_LINHA1}}</div>")
    return v


def test_renderiza_slide_e_grava_png() -> None:
    v = _vault_com_template()
    spec = DesignSpec(
        formato="carrossel",
        dimensoes=[1080, 1350],
        slides=[
            SlideSpec(
                index=1,
                template="slide-conteudo",
                conteudo={"counter": "02/03", "texto": "Erro 1: usar IA como google", "tag": "t"},
            )
        ],
    )
    w = ResolvedorTipografico(renderer=_renderer(), vault=v).resolver(spec, post_id="2026-06-12-01")
    assert w == []
    rel = f"{_FILA}/2026-06-12-01/slide-01.png"
    assert spec.slides[0].foto == rel
    assert v.read_binary(rel) == b"PNG"


def test_substitui_placeholders() -> None:
    v = _vault_com_template()
    r = _renderer()
    spec = DesignSpec(
        formato="carrossel",
        dimensoes=[1080, 1350],
        slides=[
            SlideSpec(
                index=1,
                template="slide-conteudo",
                conteudo={"counter": "02/03", "texto": "TEXTO-XYZ", "tag": "T"},
            )
        ],
    )
    ResolvedorTipografico(renderer=r, vault=v).resolver(spec, post_id="p1")
    assert "TEXTO-XYZ" in r._cap["html"] and "{{TEXTO}}" not in r._cap["html"]  # type: ignore[attr-defined]


def test_template_ausente_usa_fallback() -> None:
    v = _vault_com_template()
    spec = DesignSpec(
        formato="carrossel",
        dimensoes=[1080, 1350],
        slides=[SlideSpec(index=0, template="inexistente", conteudo={"headline_linha1": "OI"})],
    )
    w = ResolvedorTipografico(renderer=_renderer(), vault=v).resolver(spec, post_id="p1")
    assert w == [] and spec.slides[0].foto is not None
    assert spec.slides[0].foto.endswith("slide-00.png")


def test_slide_foto_hero_ignorado() -> None:
    v = _vault_com_template()
    spec = DesignSpec(
        formato="post-unico",
        dimensoes=[1080, 1350],
        slides=[
            SlideSpec(
                index=0,
                template="foto-hero",
                conteudo={},
                tema="mitos",
                foto_hero={"headline": "x"},
            )
        ],
    )
    assert ResolvedorTipografico(renderer=_renderer(), vault=v).resolver(spec, post_id="p1") == []
    assert spec.slides[0].foto is None
