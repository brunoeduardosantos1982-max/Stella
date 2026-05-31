import subprocess

from stella.adapters.higgsfield.fake import FakeHiggsField
from stella.adapters.higgsfield.mcp import HiggsFieldMCP
from stella.adapters.render.html_renderer import HtmlRenderer
from stella.agents.designer.compositor import HtmlCompositor
from stella.agents.designer.resolvedor_foto_hero import ResolvedorFotoHero
from stella.agents.designer.spec import DesignSpec, SlideSpec
from stella.framework.testing.fakes import FakeVault


def _renderer() -> HtmlRenderer:
    def run(args: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
        out = next(a.split("=", 1)[1] for a in args if a.startswith("--screenshot="))
        open(out, "wb").write(b"PNG")
        return subprocess.CompletedProcess(args, 0, "", "")

    return HtmlRenderer(browser_path="chrome", runner=run)


def test_pipeline_foto_hero_resolve() -> None:
    vault = FakeVault()
    spec = DesignSpec(
        formato="post-unico",
        dimensoes=[1080, 1350],
        slides=[
            SlideSpec(
                index=0,
                template="foto-hero",
                conteudo={},
                tema="mitos",
                foto_hero={"headline": "5 MITOS"},
            )
        ],
    )
    sp = "C04 Claude Obsidian/Stella-publicacao/pendentes/x-spec.json"
    vault.write_binary(sp, spec.to_json().encode("utf-8"))
    mcp = HiggsFieldMCP(nome="higgsfield", tipo="cli", endpoint="cli://hf", client=FakeHiggsField())
    comp = HtmlCompositor(renderer=_renderer(), vault=vault)
    r = ResolvedorFotoHero(higgs=mcp, compositor=comp, baixar=lambda u: b"HERO")
    spec2 = DesignSpec.from_json(vault.read_binary(sp).decode("utf-8"))
    w = r.resolver(spec2, post_id="2026-06-12-01")
    assert w == [] and spec2.slides[0].foto is not None
    assert spec2.slides[0].foto.endswith("hero0.png")
