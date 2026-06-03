import subprocess

from stella.adapters.higgsfield.base import HiggsFieldError
from stella.adapters.higgsfield.fake import FakeHiggsField
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


def _spec() -> DesignSpec:
    return DesignSpec(
        formato="post-unico",
        dimensoes=[1080, 1350],
        slides=[
            SlideSpec(
                index=0,
                template="foto-hero",
                conteudo={},
                tema="mitos",
                foto_hero={"headline": "5 MITOS", "anotacoes": [], "logos": []},
            )
        ],
    )


def _resolver(
    higgs: FakeHiggsField | None = None,
) -> tuple[ResolvedorFotoHero, FakeVault]:
    vault = FakeVault()
    comp = HtmlCompositor(renderer=_renderer(), vault=vault)
    return (
        ResolvedorFotoHero(
            higgs=higgs or FakeHiggsField(), compositor=comp, baixar=lambda url: b"HERO"
        ),
        vault,
    )


def test_resolve_seta_foto_do_slide() -> None:
    r, vault = _resolver()
    spec = _spec()
    w = r.resolver(spec, post_id="2026-06-12-01")
    assert w == []
    assert (
        spec.slides[0].foto
        == "C04 Claude Obsidian/Stella-publicacao/fila/2026-06-12-01/slide-00.png"
    )
    assert vault.read_binary(spec.slides[0].foto) == b"PNG"


def test_slide_sem_foto_hero_ignorado() -> None:
    r, _ = _resolver()
    spec = DesignSpec(
        formato="carrossel",
        dimensoes=[1080, 1350],
        slides=[SlideSpec(index=0, template="capa-carrossel", conteudo={})],
    )
    assert r.resolver(spec, post_id="p1") == []
    assert spec.slides[0].foto is None


def test_falha_higgs_vira_warning_intacto() -> None:
    class Quebrado(FakeHiggsField):
        def generate_image(self, prompt: str, soul_id: str | None = None) -> str:
            raise HiggsFieldError("api fora")

    r, _ = _resolver(higgs=Quebrado())
    spec = _spec()
    w = r.resolver(spec, post_id="p1")
    assert len(w) == 1 and spec.slides[0].foto is None
