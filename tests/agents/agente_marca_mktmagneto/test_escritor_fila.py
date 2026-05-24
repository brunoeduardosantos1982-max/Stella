"""Testes do EscritorFila — escreve nota .md no formato exato do publicador."""

from datetime import datetime

from stella.agents.agente_marca_mktmagneto.escritor_fila import EscritorFila
from stella.agents.agente_marca_mktmagneto.redator import PostTexto
from stella.framework.testing.fakes import FakeVault


def _post() -> PostTexto:
    return PostTexto(
        pilar=1,
        titulo="Hook",
        legenda="🔥 Hook\n\nctx\n\ncorpo\n\n👇 CTA",
        hashtags=["#a", "#b", "#c"],
        slides=["s1", "s2", "s3"],
    )


def test_escreve_nota_no_formato_do_publicador():
    vault = FakeVault({})
    e = EscritorFila(vault=vault)
    quando = datetime(2026, 5, 26, 9, 0)
    e.escrever(_post(), post_id="2026-05-26-01", png_bytes=b"PNGFAKE", agendar_para=quando)

    nota_path = "C04 Claude Obsidian/Stella-publicacao/fila/2026-05-26-01.md"
    assert vault.note_exists(nota_path)

    nota = vault.read_note(nota_path)
    fm = nota.frontmatter
    assert fm["marca"] == "mktmagneto"
    assert fm["plataformas"] == ["instagram"]
    assert fm["tipo-post"] == "feed"
    assert fm["status"] == "rascunho"
    assert fm["imagem"] == "2026-05-26-01.png"
    assert fm["agendar-para"] == "2026-05-26 09:00"  # string formatada


def test_corpo_contem_legenda_e_hashtags():
    vault = FakeVault({})
    e = EscritorFila(vault=vault)
    e.escrever(
        _post(), post_id="2026-05-26-01", png_bytes=b"PNG", agendar_para=datetime(2026, 5, 26, 9, 0)
    )

    nota = vault.read_note("C04 Claude Obsidian/Stella-publicacao/fila/2026-05-26-01.md")
    assert "🔥 Hook" in nota.content
    assert "#a" in nota.content
    assert "#c" in nota.content


def test_png_anexado_como_binario():
    vault = FakeVault({})
    e = EscritorFila(vault=vault)
    e.escrever(
        _post(),
        post_id="2026-05-26-01",
        png_bytes=b"PNGFAKE",
        agendar_para=datetime(2026, 5, 26, 9, 0),
    )

    png_path = "C04 Claude Obsidian/Stella-publicacao/fila/2026-05-26-01.png"
    assert vault.read_binary(png_path) == b"PNGFAKE"


def test_retorno_eh_o_path_da_nota():
    vault = FakeVault({})
    e = EscritorFila(vault=vault)
    path = e.escrever(
        _post(), post_id="X", png_bytes=b"P", agendar_para=datetime(2026, 5, 26, 9, 0)
    )
    assert path == "C04 Claude Obsidian/Stella-publicacao/fila/X.md"
