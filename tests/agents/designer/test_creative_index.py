"""Unit do CreativeIndex - parse tolerante e filtro de relevancia."""

from stella.agents.designer.creative_index import (
    CreativeIndex,
    ReferenceBrief,
    brief_para_prompt,
    filtrar,
    parse_index,
)

_JSON_OK = """
{
  "fotos_bruno": [
    {"arquivo": "IMG_0520.JPG", "uso_recomendado": ["autoridade"], "qualidade": "alta",
     "enquadramento": "close", "expressao": "falando", "fundo": "neutro",
     "orientacao": "retrato", "quando_usar": "capa de autoridade", "quando_evitar": "tecnico"},
    {"arquivo": "IMG_0524.JPG", "uso_recomendado": ["bastidor"], "qualidade": "media",
     "enquadramento": "meio", "expressao": "sorrindo", "fundo": "externo",
     "orientacao": "retrato", "quando_usar": "bastidor", "quando_evitar": ""}
  ],
  "referencias": [
    {"arquivo": "ref-a.jpeg", "plataforma": "instagram", "tipo_post": "carrossel",
     "padrao_visual": "numero gigante", "principios": ["1 elemento focal"],
     "quando_usar": "dado", "nao_copiar": "so a hierarquia"}
  ],
  "versao": "1.0", "atualizado_em": "2026-05-30"
}
"""


def test_parse_index_valido() -> None:
    idx = parse_index(_JSON_OK)
    assert len(idx.fotos_bruno) == 2
    assert len(idx.referencias) == 1
    assert idx.fotos_bruno[0]["arquivo"] == "IMG_0520.JPG"


def test_parse_index_json_invalido_retorna_vazio() -> None:
    idx = parse_index("isto nao e json {{{")
    assert idx.fotos_bruno == []
    assert idx.referencias == []


def test_parse_index_vazio_retorna_vazio() -> None:
    assert parse_index("").fotos_bruno == []
    assert parse_index("{}").referencias == []


def test_filtrar_limita_fotos_e_prioriza_qualidade_alta() -> None:
    idx = parse_index(_JSON_OK)
    brief = filtrar(
        idx, pauta={"tipo": "carrossel", "titulo": "x"}, copy={}, max_fotos=1, max_refs=2
    )
    assert isinstance(brief, ReferenceBrief)
    assert len(brief.fotos) == 1
    assert brief.fotos[0]["arquivo"] == "IMG_0520.JPG"


def test_filtrar_referencias_casa_tipo_post() -> None:
    idx = parse_index(_JSON_OK)
    brief = filtrar(idx, pauta={"tipo": "carrossel", "titulo": "x"}, copy={})
    assert brief.referencias[0]["arquivo"] == "ref-a.jpeg"


def test_filtrar_indice_vazio_retorna_brief_vazio() -> None:
    brief = filtrar(CreativeIndex(), pauta={"tipo": "carrossel"}, copy={})
    assert brief.fotos == []
    assert brief.referencias == []


def test_brief_para_prompt_inclui_metadados_nao_so_nomes() -> None:
    idx = parse_index(_JSON_OK)
    brief = filtrar(idx, pauta={"tipo": "carrossel", "titulo": "x"}, copy={})
    txt = brief_para_prompt(brief)
    assert "IMG_0520.JPG" in txt
    assert "autoridade" in txt
    assert "1 elemento focal" in txt


def test_brief_para_prompt_vazio_quando_sem_dados() -> None:
    assert brief_para_prompt(ReferenceBrief()) == ""
