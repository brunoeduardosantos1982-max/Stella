"""Pipeline de render unificado — slides tipograficos viram PNG na fila inline."""

import subprocess

from stella.adapters.render.html_renderer import HtmlRenderer
from stella.agents.designer.resolvedor_tipografico import ResolvedorTipografico
from stella.agents.designer.spec import DesignSpec, SlideSpec
from stella.framework.testing.fakes import FakeVault

_T = "C04 Claude Obsidian/outputs/mktmagneto-ia/templates"
_FILA = "C04 Claude Obsidian/Stella-publicacao/fila"


def _renderer() -> HtmlRenderer:
    def run(args: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
        out = next(a.split("=", 1)[1] for a in args if a.startswith("--screenshot="))
        with open(out, "wb") as f:
            f.write(b"PNG")
        return subprocess.CompletedProcess(args, 0, "", "")

    return HtmlRenderer(browser_path="chrome", runner=run)


def test_carrossel_tipografico_gera_imagens() -> None:
    v = FakeVault()
    v.write_binary(f"{_T}/capa-carrossel.html", b"<div>{{HEADLINE_LINHA1}}</div>")
    v.write_binary(f"{_T}/slide-conteudo.html", b"<div>{{TEXTO}}</div>")
    spec = DesignSpec(
        formato="carrossel",
        dimensoes=[1080, 1350],
        slides=[
            SlideSpec(index=0, template="capa-carrossel", conteudo={"headline_linha1": "H"}),
            SlideSpec(index=1, template="slide-conteudo", conteudo={"texto": "t1"}),
        ],
    )
    w = ResolvedorTipografico(renderer=_renderer(), vault=v).resolver(spec, post_id="2026-06-01-01")
    imagens = [s.foto for s in spec.slides if s.foto]
    assert w == []
    assert len(imagens) == 2
    assert all(p.startswith(_FILA) for p in imagens)
