"""Testes do DesignSpecGenerator e das dataclasses de spec."""

from stella.agents.designer.spec import DesignSpec, SlideSpec


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
