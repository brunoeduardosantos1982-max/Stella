"""Testes de roteamento por tipo de formato no DesignSpecGenerator."""

from stella.agents.designer.agent import Agent as Designer
from stella.agents.designer.spec import DesignSpec
from stella.framework.testing.fakes import FakeLLM, FakeVault

_KP = {"briefing": "Marca tech", "paleta": "#00FFFF"}
_COPY_BASE = {"legenda": "Texto do post", "slides": ["S1", "S2"], "hashtags": []}


def _make(llm_resp: str | None = None) -> tuple[Designer, FakeVault]:
    vault = FakeVault()
    resp = (
        llm_resp
        or "template_escolhido: capa-carrossel\nfoto_escolhida: \nrationale: ok\nsoul_id_prompt: null"
    )
    llm = FakeLLM(responses=[resp])
    d = Designer()
    d._vault = vault
    d._llm = type(
        "R", (), {"select": lambda self, **_: llm, "with_minimum": lambda self, m: self}
    )()
    return d, vault


def test_video_retorna_clarificacao_sem_slides() -> None:
    d, vault = _make()
    out = d.execute(
        {
            "knowledge_pack": _KP,
            "pauta": {"tipo": "video", "titulo": "Meu Reels"},
            "copy": _COPY_BASE,
        }
    )
    assert out.sucesso
    assert out.resultado["formato"] == "video"
    spec_json = vault.read_binary(out.resultado["design_spec_path"]).decode()
    spec = DesignSpec.from_json(spec_json)
    assert spec.video_clarificacao == "aguardando_input"
    assert spec.slides == []


def test_reels_tratado_como_video() -> None:
    d, vault = _make()
    out = d.execute(
        {"knowledge_pack": _KP, "pauta": {"tipo": "reels", "titulo": "Reels"}, "copy": _COPY_BASE}
    )
    assert out.resultado["formato"] == "video"


def test_landing_page_gera_html_sem_slides() -> None:
    d, vault = _make(llm_resp="<html><body>LP</body></html>")
    out = d.execute(
        {
            "knowledge_pack": _KP,
            "pauta": {"tipo": "landing-page", "titulo": "LP"},
            "copy": _COPY_BASE,
        }
    )
    assert out.sucesso
    assert out.resultado["formato"] == "landing-page"
    spec = DesignSpec.from_json(vault.read_binary(out.resultado["design_spec_path"]).decode())
    assert spec.landing_page_html is not None
    assert "<html>" in spec.landing_page_html
    assert spec.slides == []


def test_carrossel_slides_internos_usam_template_slide_conteudo() -> None:
    d, vault = _make()
    copy = {**_COPY_BASE, "slides": ["Capa", "Slide 2", "Slide 3"]}
    out = d.execute(
        {
            "knowledge_pack": _KP,
            "pauta": {"tipo": "carrossel", "titulo": "T", "n_slides": 3},
            "copy": copy,
        }
    )
    spec = DesignSpec.from_json(vault.read_binary(out.resultado["design_spec_path"]).decode())
    assert spec.slides[0].template == "capa-carrossel"
    assert spec.slides[1].template == "slide-conteudo"
    assert spec.slides[2].template == "slide-conteudo"
