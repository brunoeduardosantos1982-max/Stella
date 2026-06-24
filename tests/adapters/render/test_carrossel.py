"""Testes dos builders de carrossel (F2.1, porte do motor Field Manual escuro).

Os builders de HTML são puros (não dependem do Chrome) e por isso testáveis.
A renderização PNG em si é um wrapper fino sobre o Chrome headless.
"""

import pytest

from stella.adapters.render.carrossel import montar_slide_html, montar_slides_html

CAPA = {
    "tipo": "capa",
    "kick": "dado de mercado",
    "titulo": "76% usam IA",
    "serif": "a diferença é o sistema",
    "sub": "~ brunoe.santos",
}
CONT = {
    "tipo": "conteudo",
    "selo": "como funciona",
    "titulo": "As 3 viradas",
    "passos": [["01", "Titulo Um", "Desc um"], ["02", "Titulo Dois", "Desc dois"]],
}
CTA = {
    "tipo": "cta",
    "kick": "guarda pra depois",
    "titulo": "Salva esse post",
    "serif": "pra usar depois",
    "comenta": "Comenta <b>24</b> que eu te mando",
}


def test_capa_tem_titulo_kick_e_categoria_no_header():
    html = montar_slide_html(CAPA, 1, 3, "AGENTES DE IA")
    assert "76% usam IA" in html
    assert "dado de mercado" in html
    assert "AGENTES DE IA" in html
    assert "01 / 03" in html


def test_conteudo_tem_passos_e_selo():
    html = montar_slide_html(CONT, 2, 3, "IA")
    assert "Titulo Um" in html and "Desc um" in html and "Titulo Dois" in html
    assert "01" in html and "02" in html
    assert "como funciona" in html


def test_cta_tem_comenta_com_keyword():
    html = montar_slide_html(CTA, 3, 3, "IA")
    assert "Comenta" in html
    assert "<b>24</b>" in html


def test_nenhum_slide_tem_travessao():
    for slide in (CAPA, CONT, CTA):
        assert "—" not in montar_slide_html(slide, 1, 3, "IA")


def test_tipo_invalido_levanta_valueerror():
    with pytest.raises(ValueError):
        montar_slide_html({"tipo": "xpto"}, 1, 1, "IA")


def test_montar_slides_html_um_por_slide():
    post = {"categoria": "IA", "slides": [CAPA, CONT, CTA]}
    htmls = montar_slides_html(post)
    assert len(htmls) == 3
    assert "76% usam IA" in htmls[0]
    assert "Salva esse post" in htmls[2]
