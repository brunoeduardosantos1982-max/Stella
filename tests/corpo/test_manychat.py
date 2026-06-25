"""Testes do gerador de config ManyChat (F2.3)."""

from stella.corpo.manychat import montar_manychat
from stella.domain.registro_keywords import EntradaKeyword


def test_monta_com_keyword_posts_e_url():
    entrada = EntradaKeyword(
        keyword="MITO",
        slug="mapa-nivel-1",
        material="o mapa pra sair do nível 1",
        posts=["2026-06-03-01", "2026-06-12-01"],
    )
    txt = montar_manychat(entrada)
    assert "KEYWORD: MITO" in txt
    assert "2026-06-03-01, 2026-06-12-01" in txt
    assert "https://brunoeduardosantos.com.br/baixar/mapa-nivel-1" in txt
    assert "EU QUERO" in txt


def test_dm2_aponta_pra_landing_nao_pro_pdf():
    entrada = EntradaKeyword(keyword="VITRINE", slug="vitrine-busca-ia", posts=["p"])
    txt = montar_manychat(entrada)
    assert "brunoeduardosantos.com.br/baixar/vitrine-busca-ia" in txt
    assert "/materiais/vitrine-busca-ia.pdf" not in txt


def test_usa_o_material_no_dm():
    entrada = EntradaKeyword(keyword="ERROS", slug="diagnostico-erros-ia", material="o diagnóstico")
    txt = montar_manychat(entrada)
    assert "o diagnóstico" in txt


def test_sem_travessao():
    entrada = EntradaKeyword(keyword="24", slug="comecar-com-ia", posts=["2026-06-01-01"])
    assert "—" not in montar_manychat(entrada)
