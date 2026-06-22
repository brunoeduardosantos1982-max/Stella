from typing import Any

from stella.corpo import radar


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
