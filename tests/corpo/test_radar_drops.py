"""Testes do registro/resolução de apelidos do Radar (drop -> carrossel)."""

from stella.corpo.radar_drops import (
    carregar_drops,
    garantir_unicos,
    podar_drops,
    resolver_drop,
    salvar_drops,
    slug_apelido,
)


def test_slug_apelido_normaliza():
    assert slug_apelido("IA Google Agentes") == "ia-google-agentes"
    assert slug_apelido("Geração de Conteúdo!") == "geracao-de-conteudo"
    assert slug_apelido("  multi   espaço ") == "multi-espaco"


def test_garantir_unicos_dedup_no_lote():
    assert garantir_unicos(["a", "b"], set()) == ["a", "b"]
    assert garantir_unicos(["a", "a"], set()) == ["a", "a-2"]


def test_garantir_unicos_contra_existentes():
    assert garantir_unicos(["a"], {"a"}) == ["a-2"]
    assert garantir_unicos(["a", "a"], {"a"}) == ["a-2", "a-3"]


def _reg():
    return [
        {"apelido": "ia-google-agentes", "titulo": "Google agentes", "url": "u1"},
        {"apelido": "ia-google-gemini", "titulo": "Gemini", "url": "u2"},
        {"apelido": "mkt-funil-email", "titulo": "Funil", "url": "u3"},
    ]


def test_resolver_exato():
    achados = resolver_drop("ia-google-agentes", _reg())
    assert len(achados) == 1 and achados[0]["url"] == "u1"


def test_resolver_parcial_por_palavra():
    achados = resolver_drop("funil email", _reg())
    assert len(achados) == 1 and achados[0]["url"] == "u3"


def test_resolver_ambiguo_retorna_varios():
    achados = resolver_drop("google", _reg())
    assert len(achados) == 2


def test_resolver_inexistente_vazio():
    assert resolver_drop("xpto inexistente", _reg()) == []


def test_resolver_tolera_caixa_e_acento():
    achados = resolver_drop("IA Google Agêntes", _reg())
    assert len(achados) == 1 and achados[0]["url"] == "u1"


def test_carregar_ausente_vazio(tmp_path):
    assert carregar_drops(tmp_path / "nao.json") == []


def test_salvar_carregar_roundtrip_e_poda(tmp_path):
    from datetime import datetime, timedelta, timezone

    fuso = timezone(timedelta(hours=-3))
    agora = datetime(2026, 6, 24, 14, 0, tzinfo=fuso)
    path = tmp_path / "drops.json"
    salvar_drops([], [{"apelido": "novo-item", "titulo": "T", "url": "u"}], path=path, agora=agora)
    reg = carregar_drops(path)
    assert len(reg) == 1 and reg[0]["apelido"] == "novo-item"
    assert reg[0]["registrado_em"].startswith("2026-06-24")

    antigo = [
        {"apelido": "velho", "url": "x", "registrado_em": (agora - timedelta(days=30)).isoformat()}
    ]
    assert podar_drops(antigo, janela_dias=14, agora=agora) == []
