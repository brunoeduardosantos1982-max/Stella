from stella.domain.pacote_conteudo import PostInfo, listar_posts, resolver_pacote
from stella.domain.registro_keywords import RegistroKeywords


def _registro():
    reg = RegistroKeywords()
    reg.definir_material("VITRINE", slug="vitrine-busca-ia", material="o guia")
    reg.registrar_post("VITRINE", "2026-06-24-vitrine")
    return reg


def test_listar_posts_extrai_data(tmp_path):
    posts = listar_posts(_registro(), "vitrine", tmp_path)
    assert posts == [PostInfo(post_id="2026-06-24-vitrine", data="2026-06-24", titulo="")]


def test_listar_posts_keyword_inexistente(tmp_path):
    assert listar_posts(_registro(), "NADA", tmp_path) == []


def test_resolver_pacote_monta_paths(tmp_path):
    kw = tmp_path / "VITRINE"
    post = kw / "2026-06-24-vitrine"
    post.mkdir(parents=True)
    (post / "legenda.txt").write_text("x", encoding="utf-8")
    (post / "slide-00.png").write_bytes(b"x")
    (post / "slide-01.png").write_bytes(b"x")
    (kw / "vitrine-busca-ia.pdf").write_bytes(b"%PDF")
    pac = resolver_pacote(_registro(), "vitrine", "2026-06-24-vitrine", tmp_path)
    assert pac.legenda == post / "legenda.txt"
    assert pac.slides == [post / "slide-00.png", post / "slide-01.png"]
    assert pac.material_pdf == kw / "vitrine-busca-ia.pdf"


def test_resolver_pacote_ausentes_viram_none(tmp_path):
    pac = resolver_pacote(_registro(), "vitrine", "2026-06-24-vitrine", tmp_path)
    assert pac.legenda is None and pac.slides == [] and pac.material_pdf is None
