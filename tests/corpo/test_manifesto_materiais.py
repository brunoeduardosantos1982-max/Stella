"""Testes do manifesto de materiais (slug -> titulo/descricao/pdf) lido pela landing."""

import json

from stella.corpo.manifesto_materiais import atualizar_manifesto, montar_entrada_manifesto


def test_montar_entrada():
    e = montar_entrada_manifesto("vitrine-busca-ia", "Vitrine da IA", "Guia de presença")
    assert e == {
        "titulo": "Vitrine da IA",
        "descricao": "Guia de presença",
        "pdf": "/materiais/vitrine-busca-ia.pdf",
    }


def test_atualizar_cria_e_faz_merge(tmp_path):
    path = tmp_path / "manifesto.json"
    atualizar_manifesto(path, "a", "Ta", "Da")
    atualizar_manifesto(path, "b", "Tb", "Db")
    dados = json.loads(path.read_text(encoding="utf-8"))
    assert set(dados) == {"a", "b"}
    assert dados["a"]["pdf"] == "/materiais/a.pdf"
    # re-escrever a mesma keyword sobrescreve, nao duplica
    atualizar_manifesto(path, "a", "Ta2", "Da2")
    dados = json.loads(path.read_text(encoding="utf-8"))
    assert dados["a"]["titulo"] == "Ta2" and set(dados) == {"a", "b"}
    assert not (path.parent / (path.name + ".tmp")).exists()
