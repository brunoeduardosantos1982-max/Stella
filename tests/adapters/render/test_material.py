"""Testes do material rico (F2.2): contagem de seções/páginas, fontes e layout.

As funções puras travam a REGRA DE LAYOUT (nº de <section class="page"> deve bater
com o nº de páginas do PDF) que causou o bug de espaçamento corrigido na produção.
"""

import pytest

from stella.adapters.render.material import (
    contar_paginas_pdf,
    contar_secoes,
    fontes_embutidas,
    validar_layout,
    validar_material,
    validar_riqueza,
)


def test_contar_secoes():
    html = '<body><section class="page">a</section><section class="page">b</section></body>'
    assert contar_secoes(html) == 2


def test_contar_paginas_pdf_ignora_node_pages():
    # /Type /Pages (plural, o nó-árvore) não conta; /Type /Page (folha) conta.
    fake = b"/Type /Pages /Kids ... /Type /Page x /Type /Page y /Type /Page z"
    assert contar_paginas_pdf(fake) == 3


def test_fontes_embutidas_detecta():
    assert fontes_embutidas(b"...ABCDEE+SpaceGrotesk... ...Fraunces...") is True
    assert fontes_embutidas(b"sem fontes aqui") is False


def test_validar_layout_ok_quando_bate():
    html = '<section class="page">1</section><section class="page">2</section>'
    validar_layout(html, n_paginas=2)  # não levanta


def test_validar_layout_estourou_levanta_com_mensagem():
    html = '<section class="page">unica</section>'
    with pytest.raises(ValueError) as exc:
        validar_layout(html, n_paginas=3)
    assert "1" in str(exc.value) and "3" in str(exc.value)


_PAGINA = '<section class="page">{}</section>'


def test_riqueza_aceita_copybox():
    validar_riqueza('<div class="copybox">cole isto</div>')  # não levanta


def test_riqueza_aceita_checklist_e_flow():
    validar_riqueza('<div class="checklist">...</div>')
    validar_riqueza('<div class="flow">a→b</div>')


def test_riqueza_rejeita_so_prosa():
    with pytest.raises(ValueError, match="material raso"):
        validar_riqueza('<div class="camada"><p>só texto conceitual</p></div>')


def test_riqueza_nao_confunde_substring():
    # "flowchart-legacy" não conta como classe flow
    with pytest.raises(ValueError):
        validar_riqueza('<div class="flowchart-legacy">x</div>')


def test_validar_material_ok():
    html = _PAGINA.format('<div class="copybox">x</div>')
    validar_material(html, 1)  # 1 seção == 1 página e tem bloco acionável


def test_validar_material_reprova_layout():
    with pytest.raises(ValueError, match="estourou"):
        validar_material(_PAGINA.format('<div class="copybox">x</div>'), 2)


def test_validar_material_reprova_raso():
    with pytest.raises(ValueError, match="material raso"):
        validar_material(_PAGINA.format("<p>prosa</p>"), 1)
