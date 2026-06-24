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
    assert "https://brunoeduardosantos.com.br/materiais/mapa-nivel-1.pdf" in txt
    assert "EU QUERO" in txt


def test_usa_o_material_no_dm():
    entrada = EntradaKeyword(keyword="ERROS", slug="diagnostico-erros-ia", material="o diagnóstico")
    txt = montar_manychat(entrada)
    assert "o diagnóstico" in txt


def test_sem_travessao():
    entrada = EntradaKeyword(keyword="24", slug="comecar-com-ia", posts=["2026-06-01-01"])
    assert "—" not in montar_manychat(entrada)
