"""Testes do DesignSpecGenerator e das dataclasses de spec."""

from stella.agents.designer.agent import Agent as Designer
from stella.agents.designer.spec import DesignSpec, SlideSpec
from stella.framework.testing.fakes import FakeLLM, FakeVault


def test_spec_serializa_e_desserializa() -> None:
    spec = DesignSpec(
        formato="carrossel",
        dimensoes=[1080, 1350],
        slides=[
            SlideSpec(
                index=0,
                template="capa-foto-split",
                conteudo={"headline_linha1": "Como a IA", "headline_destaque": "mudou"},
                foto="foto-01.jpg",
            ),
            SlideSpec(index=1, template="slide-conteudo", conteudo={"texto": "Slide 2"}),
        ],
    )
    json_str = spec.to_json()
    recuperado = DesignSpec.from_json(json_str)

    assert recuperado.formato == "carrossel"
    assert recuperado.dimensoes == [1080, 1350]
    assert len(recuperado.slides) == 2
    assert recuperado.slides[0].template == "capa-foto-split"
    assert recuperado.slides[0].foto == "foto-01.jpg"
    assert recuperado.slides[1].soul_id_prompt is None
    assert recuperado.status == "pending_render"


def test_spec_video_nao_tem_slides() -> None:
    spec = DesignSpec(
        formato="video",
        dimensoes=[],
        video_clarificacao="aguardando_input",
    )
    assert spec.slides == []
    assert spec.landing_page_html is None


def test_spec_landing_page_tem_html() -> None:
    spec = DesignSpec(
        formato="landing-page",
        dimensoes=[],
        landing_page_html="<html><body>Olá</body></html>",
    )
    json_str = spec.to_json()
    rec = DesignSpec.from_json(json_str)
    assert rec.landing_page_html == "<html><body>Olá</body></html>"
    assert rec.slides == []


def test_slidespec_referencias_usadas_default_vazio() -> None:
    s = SlideSpec(index=0, template="capa-carrossel", conteudo={})
    assert s.referencias_usadas == []


def test_designspec_roundtrip_preserva_referencias_usadas() -> None:
    s = SlideSpec(
        index=0,
        template="capa-foto-split",
        conteudo={"headline_linha1": "X"},
        foto="IMG_0520.JPG",
        referencias_usadas=["ref-a.jpeg"],
    )
    spec = DesignSpec(formato="carrossel", dimensoes=[1080, 1350], slides=[s])
    restaurado = DesignSpec.from_json(spec.to_json())
    assert restaurado.slides[0].referencias_usadas == ["ref-a.jpeg"]


def test_designspec_from_json_aceita_spec_antigo_sem_referencias() -> None:
    """Specs gravados antes deste campo nao devem quebrar o parse."""
    antigo = (
        '{"formato":"carrossel","dimensoes":[1080,1350],"slides":'
        '[{"index":0,"template":"capa-carrossel","conteudo":{}}]}'
    )
    spec = DesignSpec.from_json(antigo)
    assert spec.slides[0].referencias_usadas == []


_FOTO_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

_KP = {"voz": "direto", "paleta": {"primaria": "#00FFFF"}, "briefing": "Marca tech"}
_COPY = {
    "legenda": "Hook\n\nContexto\n\nCTA",
    "slides": ["Slide 1", "Slide 2", "Slide 3"],
    "hashtags": ["#ia"],
}
_PAUTA_CARROSSEL = {
    "pilar": 1,
    "titulo": "Como a IA mudou meu negócio",
    "tipo": "carrossel",
    "n_slides": 3,
}
_PAUTA_POST = {
    "pilar": 2,
    "titulo": "Dica rápida de produtividade",
    "tipo": "post-unico",
    "n_slides": 1,
}
_PAUTA_STORIES = {"pilar": 3, "titulo": "Nos bastidores", "tipo": "stories", "n_slides": 1}

_LLM_SPEC_RESP = """
template_escolhido: capa-carrossel
foto_escolhida: ""
rationale: "Conteúdo conceitual"
soul_id_prompt: null
"""


def _make_designer(responses: list[str] | None = None) -> tuple[Designer, FakeVault]:
    vault = FakeVault()
    llm = FakeLLM(responses=responses or [_LLM_SPEC_RESP])
    designer = Designer()
    designer._vault = vault
    designer._llm = type(
        "R", (), {"select": lambda self, **_: llm, "with_minimum": lambda self, m: self}
    )()
    return designer, vault


def test_carrossel_gera_spec_com_n_slides() -> None:
    designer, vault = _make_designer()
    out = designer.execute({"knowledge_pack": _KP, "pauta": _PAUTA_CARROSSEL, "copy": _COPY})
    assert out.sucesso
    spec_path = out.resultado["design_spec_path"]
    assert spec_path.endswith("-spec.json")
    spec_json = vault.read_binary(spec_path).decode("utf-8")
    spec = DesignSpec.from_json(spec_json)
    assert spec.formato == "carrossel"
    assert spec.dimensoes == [1080, 1350]
    assert len(spec.slides) == 3  # capa + 2 slides internos
    assert spec.slides[0].template == "capa-carrossel"
    assert spec.slides[1].template == "slide-conteudo"
    assert spec.status == "pending_render"


def test_post_unico_gera_spec_com_1_slide() -> None:
    designer, vault = _make_designer()
    out = designer.execute(
        {"knowledge_pack": _KP, "pauta": _PAUTA_POST, "copy": {**_COPY, "slides": ["Slide único"]}}
    )
    assert out.sucesso
    spec_json = vault.read_binary(out.resultado["design_spec_path"]).decode("utf-8")
    spec = DesignSpec.from_json(spec_json)
    assert spec.formato == "post-unico"
    assert len(spec.slides) == 1


def test_stories_tem_dimensao_correta() -> None:
    designer, vault = _make_designer()
    out = designer.execute(
        {"knowledge_pack": _KP, "pauta": _PAUTA_STORIES, "copy": {**_COPY, "slides": ["Story"]}}
    )
    assert out.sucesso
    spec_json = vault.read_binary(out.resultado["design_spec_path"]).decode("utf-8")
    spec = DesignSpec.from_json(spec_json)
    assert spec.formato == "stories"
    assert spec.dimensoes == [1080, 1920]
