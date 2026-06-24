"""Testes do registro de keywords da fábrica de conteúdo v2 (F1).

Fonte da verdade keyword -> slug -> material -> posts, com matching
acento/caixa-insensível, dedup de material e persistência atômica em JSON.
"""

from stella.domain.registro_keywords import (
    EntradaKeyword,
    RegistroKeywords,
    normalizar_keyword,
)


def test_normalizar_remove_acento_e_caixa():
    assert normalizar_keyword("Governança") == "GOVERNANCA"
    assert normalizar_keyword("  2026 ") == "2026"
    assert normalizar_keyword("agente") == "AGENTE"


def test_buscar_e_acento_insensivel():
    reg = RegistroKeywords()
    reg.registrar_post("GOVERNANÇA", "2026-06-01-03", slug="governanca-agentes")
    achado = reg.buscar("governanca")
    assert achado is not None
    assert achado.keyword == "GOVERNANÇA"
    assert achado.slug == "governanca-agentes"


def test_tem_material_e_dedup_mantem_slug():
    reg = RegistroKeywords()
    reg.registrar_post("MITO", "2026-06-03-01", slug="mapa-nivel-1", material="O mapa")
    # segundo post na MESMA keyword, sem novo material: dedup mantém slug e acumula post
    reg.registrar_post("mito", "2026-06-12-01")
    entrada = reg.buscar("MITO")
    assert entrada is not None
    assert reg.tem_material("MITO") is True
    assert entrada.slug == "mapa-nivel-1"
    assert entrada.posts == ["2026-06-03-01", "2026-06-12-01"]


def test_registrar_post_nao_duplica_id():
    reg = RegistroKeywords()
    reg.registrar_post("ERROS", "2026-06-08-01", slug="diagnostico-erros-ia")
    reg.registrar_post("ERROS", "2026-06-08-01")
    entrada = reg.buscar("ERROS")
    assert entrada is not None
    assert entrada.posts == ["2026-06-08-01"]


def test_tem_material_falso_sem_slug():
    reg = RegistroKeywords()
    reg.registrar_post("24", "2026-06-01-01")
    assert reg.tem_material("24") is False


def test_carregar_arquivo_inexistente_devolve_vazio(tmp_path):
    reg = RegistroKeywords.carregar(tmp_path / "nao-existe.json")
    assert reg.keywords() == []


def test_salvar_e_recarregar_roundtrip_atomico(tmp_path):
    path = tmp_path / "sub" / "registro-keywords.json"
    reg = RegistroKeywords()
    reg.registrar_post("STACK", "2026-06-05-02", slug="stack-diagrama", material="diagrama")
    reg.registrar_post("STACK", "2026-06-17-02")
    reg.salvar(path)

    # escrita atômica: não deixa .tmp para trás
    assert not (path.parent / (path.name + ".tmp")).exists()

    recarregado = RegistroKeywords.carregar(path)
    entrada = recarregado.buscar("stack")
    assert entrada == EntradaKeyword(
        keyword="STACK",
        slug="stack-diagrama",
        material="diagrama",
        posts=["2026-06-05-02", "2026-06-17-02"],
    )
