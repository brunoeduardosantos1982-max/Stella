"""Testes do ResolvedorImagens."""

from stella.adapters.higgsfield.base import HiggsFieldError
from stella.adapters.higgsfield.fake import FakeHiggsField
from stella.adapters.higgsfield.resolvedor import ResolvedorImagens
from stella.agents.designer.spec import DesignSpec, SlideSpec
from stella.framework.testing.fakes import FakeVault


def _spec_com_higgsfield() -> DesignSpec:
    return DesignSpec(
        formato="carrossel",
        dimensoes=[1080, 1350],
        slides=[
            SlideSpec(
                index=0,
                template="capa-foto-bg",
                conteudo={},
                soul_id_prompt="Bruno em palco tech",
            ),
            SlideSpec(index=1, template="slide-conteudo", conteudo={"texto": "x"}),
        ],
    )


def test_resolve_slide_higgsfield_seta_foto_e_limpa_prompt() -> None:
    vault = FakeVault()
    higgs = FakeHiggsField()
    spec = _spec_com_higgsfield()

    warnings = ResolvedorImagens(higgs=higgs, vault=vault, baixar=lambda url: b"PNGDATA").resolver(
        spec, post_id="2026-06-01-01"
    )

    assert warnings == []
    slide = spec.slides[0]
    assert (
        slide.foto == "C04 Claude Obsidian/outputs/mktmagneto-ia/imagens/2026-06-01-01/slide0.png"
    )
    assert slide.soul_id_prompt is None
    assert vault.read_binary(slide.foto) == b"PNGDATA"
    assert len(higgs.calls) == 1
    assert higgs.calls[0]["prompt"] == "Bruno em palco tech"


def test_slide_sem_soul_id_prompt_e_ignorado() -> None:
    vault = FakeVault()
    higgs = FakeHiggsField()
    spec = _spec_com_higgsfield()

    ResolvedorImagens(higgs=higgs, vault=vault, baixar=lambda url: b"X").resolver(
        spec, post_id="p1"
    )

    assert len(higgs.calls) == 1  # só o slide 0 tinha soul_id_prompt
    assert spec.slides[1].foto is None


def test_slide_ja_com_foto_e_ignorado_idempotente() -> None:
    vault = FakeVault()
    higgs = FakeHiggsField()
    spec = _spec_com_higgsfield()
    spec.slides[0].foto = "ja/existe.png"

    ResolvedorImagens(higgs=higgs, vault=vault, baixar=lambda url: b"X").resolver(
        spec, post_id="p1"
    )

    assert len(higgs.calls) == 0


def test_falha_de_geracao_mantem_intencao_e_retorna_warning() -> None:
    vault = FakeVault()

    class _HiggsQuebrado(FakeHiggsField):
        def generate_image(self, prompt: str, soul_id=None) -> str:
            raise HiggsFieldError("api fora")

    spec = _spec_com_higgsfield()
    warnings = ResolvedorImagens(
        higgs=_HiggsQuebrado(), vault=vault, baixar=lambda url: b"X"
    ).resolver(spec, post_id="p1")

    assert len(warnings) == 1
    assert "slide 0" in warnings[0]
    assert spec.slides[0].foto is None
    assert spec.slides[0].soul_id_prompt == "Bruno em palco tech"  # intenção preservada


def test_falha_de_download_mantem_intencao_e_retorna_warning() -> None:
    vault = FakeVault()
    spec = _spec_com_higgsfield()

    def _baixar_quebrado(url: str) -> bytes:
        raise OSError("rede caiu")

    warnings = ResolvedorImagens(
        higgs=FakeHiggsField(), vault=vault, baixar=_baixar_quebrado
    ).resolver(spec, post_id="p1")

    assert len(warnings) == 1
    assert spec.slides[0].foto is None
    assert spec.slides[0].soul_id_prompt is not None
