from stella.agents.designer.temas.base import FotoHeroContent
from stella.agents.designer.temas.registry import TEMAS, get_tema


def _content() -> FotoHeroContent:
    return FotoHeroContent(
        headline="5 MITOS\nSOBRE IA",
        sublabel="e a verdade que ninguém te conta",
        label_topo="PARE DE ACREDITAR\nNESSES MITOS",
        anotacoes=["conversar com IA não é usar IA ->", "<- quem constrói sai do nível 1"],
        logos=["claude", "openai"],
        counter="01 / 03",
    )


def test_registry_tem_mitos() -> None:
    assert "mitos" in TEMAS
    assert get_tema("mitos").nome == "mitos"


def test_mitos_hf_prompt_pede_careca_e_flatlay() -> None:
    p = get_tema("mitos").hf_prompt().lower()
    assert "careca" in p and ("top-down" in p or "de cima" in p)


def test_mitos_html_inclui_conteudo_e_imagem() -> None:
    html = get_tema("mitos").html(_content(), "data:image/png;base64,AAAA")
    assert "5 MITOS" in html
    assert "data:image/png;base64,AAAA" in html
    assert "conversar com IA" in html
    assert "PARE DE ACREDITAR" in html
    assert "svg" in html.lower()


def test_tech_html_inclui_conteudo_e_imagem() -> None:
    html = get_tema("tech").html(_content(), "data:image/png;base64,TECH")
    assert get_tema("tech").nome == "tech"
    assert get_tema("tech").usa_soul is True
    assert "5 MITOS" in html
    assert "data:image/png;base64,TECH" in html
    assert "conversar com IA" in html


def test_impactante_html_inclui_conteudo_e_imagem() -> None:
    html = get_tema("impactante").html(_content(), "data:image/png;base64,IMPACTANTE")
    assert get_tema("impactante").nome == "impactante"
    assert get_tema("impactante").usa_soul is True
    assert "5 MITOS" in html
    assert "data:image/png;base64,IMPACTANTE" in html
    assert "ningu" in html


def test_segredos_html_inclui_conteudo_sem_imagem() -> None:
    html = get_tema("segredos").html(_content(), "data:image/png;base64,SEGREDOS")
    assert get_tema("segredos").nome == "segredos"
    assert get_tema("segredos").usa_soul is False
    assert "5 MITOS" in html
    assert "conversar com IA" in html
    assert "data:image/png;base64,SEGREDOS" not in html


def test_autoridade_html_inclui_conteudo_e_imagem() -> None:
    html = get_tema("autoridade").html(_content(), "data:image/png;base64,AUTORIDADE")
    assert get_tema("autoridade").nome == "autoridade"
    assert get_tema("autoridade").usa_soul is True
    assert "5 MITOS" in html
    assert "data:image/png;base64,AUTORIDADE" in html
    assert "PARE DE ACREDITAR" in html


def test_dicas_html_inclui_conteudo_e_imagem() -> None:
    html = get_tema("dicas").html(_content(), "data:image/png;base64,DICAS")
    assert get_tema("dicas").nome == "dicas"
    assert get_tema("dicas").usa_soul is True
    assert "5 MITOS" in html
    assert "data:image/png;base64,DICAS" in html
    assert "ningu" in html


def test_ferramentas_html_inclui_conteudo_e_imagem() -> None:
    html = get_tema("ferramentas").html(_content(), "data:image/png;base64,FERRAMENTAS")
    assert get_tema("ferramentas").nome == "ferramentas"
    assert get_tema("ferramentas").usa_soul is True
    assert "5 MITOS" in html
    assert "data:image/png;base64,FERRAMENTAS" in html
    assert "PARE DE ACREDITAR" in html


def test_automatizacao_html_inclui_conteudo_e_imagem() -> None:
    html = get_tema("automatizacao").html(_content(), "data:image/png;base64,AUTO")
    assert get_tema("automatizacao").nome == "automatizacao"
    assert get_tema("automatizacao").usa_soul is True
    assert "5 MITOS" in html
    assert "data:image/png;base64,AUTO" in html
    assert "ningu" in html
