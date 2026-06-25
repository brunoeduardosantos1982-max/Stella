"""Testes do publicar-material (F2.4, gate 2).

O commit+deploy fica atrás de uma fronteira injetável (deploy_fn) para os testes
não tocarem na rede. Aqui validamos a orquestração: cópia, guard e chamada.
"""

import pytest

from stella.corpo.publicar_material import encontrar_pdf, publicar_material


def test_encontrar_pdf_acha_na_subpasta_da_keyword(tmp_path):
    (tmp_path / "ERROS").mkdir()
    (tmp_path / "ERROS" / "diagnostico-erros-ia.pdf").write_bytes(b"%PDF")
    achado = encontrar_pdf(tmp_path, "diagnostico-erros-ia")
    assert achado.name == "diagnostico-erros-ia.pdf"


def test_encontrar_pdf_ausente_levanta(tmp_path):
    with pytest.raises(FileNotFoundError):
        encontrar_pdf(tmp_path, "nao-existe")


def test_publicar_copia_pro_hub_e_chama_deploy(tmp_path):
    fab = tmp_path / "fab"
    (fab / "ERROS").mkdir(parents=True)
    (fab / "ERROS" / "diag.pdf").write_bytes(b"%PDF-conteudo")
    hub = tmp_path / "hub" / "materiais"
    chamado = {}

    def fake_deploy(slug: str, destino) -> str:
        chamado["slug"] = slug
        return f"https://www.brunoeduardosantos.com.br/materiais/{slug}.pdf"

    url = publicar_material("diag", fab_dir=fab, hub_materiais=hub, deploy_fn=fake_deploy)
    assert (hub / "diag.pdf").read_bytes() == b"%PDF-conteudo"
    assert chamado["slug"] == "diag"
    assert url.endswith("/diag.pdf")


def test_publicar_sem_pdf_nao_deploya(tmp_path):
    fab = tmp_path / "fab"
    fab.mkdir()
    contador = {"n": 0}

    def fake_deploy(slug: str, destino) -> str:
        contador["n"] += 1
        return "x"

    with pytest.raises(FileNotFoundError):
        publicar_material("xpto", fab_dir=fab, hub_materiais=tmp_path / "h", deploy_fn=fake_deploy)
    assert contador["n"] == 0


def test_publicar_chama_manifesto_com_titulo(tmp_path):
    fab = tmp_path / "fab"
    (fab / "VITRINE").mkdir(parents=True)
    (fab / "VITRINE" / "v.pdf").write_bytes(b"%PDF")
    chamado: dict[str, str] = {}

    def fake_manifesto(slug: str, titulo: str, descricao: str) -> None:
        chamado.update(slug=slug, titulo=titulo, descricao=descricao)

    publicar_material(
        "v",
        fab_dir=fab,
        hub_materiais=tmp_path / "h",
        deploy_fn=lambda s, d: "url",
        manifesto_fn=fake_manifesto,
        titulo="Vitrine da IA",
        descricao="Guia",
    )
    assert chamado == {"slug": "v", "titulo": "Vitrine da IA", "descricao": "Guia"}


def test_publicar_sem_titulo_nao_chama_manifesto(tmp_path):
    fab = tmp_path / "fab"
    (fab / "X").mkdir(parents=True)
    (fab / "X" / "v.pdf").write_bytes(b"%PDF")
    n = {"c": 0}
    publicar_material(
        "v",
        fab_dir=fab,
        hub_materiais=tmp_path / "h",
        deploy_fn=lambda s, d: "url",
        manifesto_fn=lambda s, t, d: n.update(c=n["c"] + 1),
    )
    assert n["c"] == 0
