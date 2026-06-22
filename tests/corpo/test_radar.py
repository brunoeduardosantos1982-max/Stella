import json
from datetime import datetime
from pathlib import Path
from typing import Any

from stella.corpo import radar


def _cand(url: str) -> radar.Candidato:
    return radar.Candidato(titulo="t", url=url, veiculo="v", snippet="s", data="d", tema="IA")


def test_filtrar_novos_remove_urls_ja_vistas() -> None:
    seen = [{"url": "https://x.com/velho", "enviado_em": "2026-06-20T10:00:00-03:00"}]
    cands = [_cand("https://x.com/velho"), _cand("https://x.com/novo")]
    novos = radar.filtrar_novos(cands, seen)
    assert [c.url for c in novos] == ["https://x.com/novo"]


def test_podar_seen_descarta_entradas_antigas() -> None:
    agora = datetime(2026, 6, 21, 12, 0, tzinfo=radar.FUSO)
    seen = [
        {"url": "a", "enviado_em": "2026-06-20T12:00:00-03:00"},  # 1 dia: fica
        {"url": "b", "enviado_em": "2026-06-01T12:00:00-03:00"},  # 20 dias: sai
    ]
    podado = radar.podar_seen(seen, janela_dias=7, agora=agora)
    assert [s["url"] for s in podado] == ["a"]


def test_gravar_seen_anexa_urls_com_timestamp(tmp_path: Path) -> None:
    p = tmp_path / "seen.json"
    agora = datetime(2026, 6, 21, 6, 0, tzinfo=radar.FUSO)
    radar.gravar_seen([], ["https://x.com/novo"], path=p, agora=agora)
    dados = json.loads(p.read_text(encoding="utf-8"))
    assert dados[0]["url"] == "https://x.com/novo"
    assert dados[0]["enviado_em"].startswith("2026-06-21T06:00")


def test_buscar_candidatos_agrega_temas_e_deduplica_por_url() -> None:
    chamadas: list[str] = []

    def buscar_fake(query: str, api_key: str, **kwargs: Any) -> list[dict[str, Any]]:
        chamadas.append(query)
        return [
            {
                "titulo": f"Artigo de {query}",
                "url": "https://x.com/a" if query == "marketing" else "https://x.com/b",
                "veiculo": "x.com",
                "snippet": "s",
                "data": "2026-06-21",
            }
        ]

    cands = radar.buscar_candidatos(
        temas=["marketing", "IA", "tecnologia"],
        api_key="k",
        buscar=buscar_fake,
    )

    # uma busca por tema
    assert chamadas == ["marketing", "IA", "tecnologia"]
    # url repetida (IA e tecnologia retornaram /b) deduplicada
    urls = sorted(c.url for c in cands)
    assert urls == ["https://x.com/a", "https://x.com/b"]
    assert all(isinstance(c, radar.Candidato) for c in cands)
    # o tema fica registrado
    assert {c.tema for c in cands} == {"marketing", "IA"}
