"""Testes do GanchoCatalog."""

from stella.agents.copywriter.ganchos import GanchoCatalog


def test_lista_e_get(tmp_path) -> None:
    p = tmp_path / "swipe.json"
    p.write_text(
        '{"padroes":[{"id":"x","nome":"X","estrutura":"a+b","quando_usar":"q"}]}',
        encoding="utf-8",
    )
    cat = GanchoCatalog(path=str(p))
    assert [g["id"] for g in cat.listar()] == ["x"]
    assert cat.get("x")["nome"] == "X"


def test_arquivo_ausente_lista_vazia(tmp_path) -> None:
    cat = GanchoCatalog(path=str(tmp_path / "nao-existe.json"))
    assert cat.listar() == []
    assert cat.get("x") is None
