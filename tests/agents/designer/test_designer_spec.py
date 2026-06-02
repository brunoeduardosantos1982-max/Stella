"""Testes do DesignSpecGenerator e das dataclasses de spec."""

import json as _json
from typing import Any

import pytest

from stella.agents.designer.agent import Agent as Designer
from stella.agents.designer.agent import _limpar_texto_slide
from stella.agents.designer.spec import DesignSpec, SlideSpec
from stella.framework.testing.fakes import FakeLLM, FakeVault


def test_spec_serializa_e_desserializa() -> None:
    spec = DesignSpec(
        formato="carrossel",
        dimensoes=[1080, 1350],
        slides=[
            SlideSpec(
                index=0,
                template="capa-foto-split",
                conteudo={"headline_linha1": "Como a IA", "headline_destaque": "mudou"},
                foto="foto-01.jpg",
            ),
            SlideSpec(index=1, template="slide-conteudo", conteudo={"texto": "Slide 2"}),
        ],
    )
    json_str = spec.to_json()
    recuperado = DesignSpec.from_json(json_str)

    assert recuperado.formato == "carrossel"
    assert recuperado.dimensoes == [1080, 1350]
    assert len(recuperado.slides) == 2
    assert recuperado.slides[0].template == "capa-foto-split"
    assert recuperado.slides[0].foto == "foto-01.jpg"
    assert recuperado.slides[1].soul_id_prompt is None
    assert recuperado.status == "pending_render"


def test_spec_video_nao_tem_slides() -> None:
    spec = DesignSpec(
        formato="video",
        dimensoes=[],
        video_clarificacao="aguardando_input",
    )
    assert spec.slides == []
    assert spec.landing_page_html is None


def test_spec_landing_page_tem_html() -> None:
    spec = DesignSpec(
        formato="landing-page",
        dimensoes=[],
        landing_page_html="<html><body>Olá</body></html>",
    )
    json_str = spec.to_json()
    rec = DesignSpec.from_json(json_str)
    assert rec.landing_page_html == "<html><body>Olá</body></html>"
    assert rec.slides == []


def test_slidespec_referencias_usadas_default_vazio() -> None:
    s = SlideSpec(index=0, template="capa-carrossel", conteudo={})
    assert s.referencias_usadas == []


def test_designspec_roundtrip_preserva_referencias_usadas() -> None:
    s = SlideSpec(
        index=0,
        template="capa-foto-split",
        conteudo={"headline_linha1": "X"},
        foto="IMG_0520.JPG",
        referencias_usadas=["ref-a.jpeg"],
    )
    spec = DesignSpec(formato="carrossel", dimensoes=[1080, 1350], slides=[s])
    restaurado = DesignSpec.from_json(spec.to_json())
    assert restaurado.slides[0].referencias_usadas == ["ref-a.jpeg"]


def test_slidespec_foto_hero_roundtrip_json() -> None:
    spec = DesignSpec(
        formato="post-unico",
        dimensoes=[1080, 1350],
        slides=[
            SlideSpec(
                index=0,
                template="foto-hero",
                conteudo={},
                tema="mitos",
                foto_hero={"headline": "5 MITOS", "logos": ["claude", "openai"]},
            ),
        ],
    )

    recuperado = DesignSpec.from_json(spec.to_json())

    assert recuperado.slides[0].tema == "mitos"
    assert recuperado.slides[0].foto_hero is not None
    assert recuperado.slides[0].foto_hero["headline"] == "5 MITOS"


def test_designspec_from_json_aceita_spec_antigo_sem_referencias() -> None:
    """Specs gravados antes deste campo nao devem quebrar o parse."""
    antigo = (
        '{"formato":"carrossel","dimensoes":[1080,1350],"slides":'
        '[{"index":0,"template":"capa-carrossel","conteudo":{}}]}'
    )
    spec = DesignSpec.from_json(antigo)
    assert spec.slides[0].referencias_usadas == []


_FOTO_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

_KP = {"voz": "direto", "paleta": {"primaria": "#00FFFF"}, "briefing": "Marca tech"}
_COPY = {
    "legenda": "Hook\n\nContexto\n\nCTA",
    "slides": ["Slide 1", "Slide 2", "Slide 3"],
    "hashtags": ["#ia"],
}
_PAUTA_CARROSSEL = {
    "pilar": 1,
    "titulo": "Como a IA mudou meu negócio",
    "tipo": "carrossel",
    "n_slides": 3,
}
_PAUTA_POST = {
    "pilar": 2,
    "titulo": "Dica rápida de produtividade",
    "tipo": "post-unico",
    "n_slides": 1,
}
_PAUTA_STORIES = {"pilar": 3, "titulo": "Nos bastidores", "tipo": "stories", "n_slides": 1}

_LLM_SPEC_RESP = """
template_escolhido: capa-carrossel
foto_escolhida: ""
rationale: "Conteúdo conceitual"
soul_id_prompt: null
"""

_INDEX_JSON = _json.dumps(
    {
        "fotos_bruno": [
            {
                "arquivo": "IMG_0520.JPG",
                "uso_recomendado": ["autoridade"],
                "qualidade": "alta",
                "enquadramento": "close",
                "expressao": "falando",
                "fundo": "neutro",
                "orientacao": "retrato",
                "quando_usar": "autoridade",
                "quando_evitar": "tecnico",
            }
        ],
        "referencias": [
            {
                "arquivo": "ref-a.jpeg",
                "plataforma": "instagram",
                "tipo_post": "carrossel",
                "padrao_visual": "numero gigante",
                "principios": ["1 elemento focal"],
                "quando_usar": "dado",
                "nao_copiar": "so hierarquia",
            }
        ],
    },
    ensure_ascii=False,
)


@pytest.fixture
def designer_com_indice():
    def _build(index_json: str | None, escolha_yaml: str):
        class _Vault(FakeVault):
            def read_binary(self, path: str) -> bytes:
                if index_json is not None and path.endswith("creative-index.json"):
                    return index_json.encode("utf-8")
                raise FileNotFoundError(path)

            def write_binary(self, path: str, dados: bytes) -> None:
                return None

            def list_files_in_folder(self, folder: str, extensions: Any = None) -> list[str]:
                return []

        fake_llm = FakeLLM(responses=[escolha_yaml])

        class _Router:
            def select(self, complexity: str = "low") -> FakeLLM:
                return fake_llm

        agent = Designer(llm=_Router(), vault=_Vault())  # type: ignore[arg-type]
        return agent, fake_llm

    return _build


def _make_designer(responses: list[str] | None = None) -> tuple[Designer, FakeVault]:
    vault = FakeVault()
    llm = FakeLLM(responses=responses or [_LLM_SPEC_RESP])
    designer = Designer()
    designer._vault = vault
    designer._llm = type(
        "R", (), {"select": lambda self, **_: llm, "with_minimum": lambda self, m: self}
    )()
    return designer, vault


def test_carrossel_gera_spec_com_n_slides() -> None:
    designer, vault = _make_designer()
    out = designer.execute({"knowledge_pack": _KP, "pauta": _PAUTA_CARROSSEL, "copy": _COPY})
    assert out.sucesso
    spec_path = out.resultado["design_spec_path"]
    assert spec_path.endswith("-spec.json")
    spec_json = vault.read_binary(spec_path).decode("utf-8")
    spec = DesignSpec.from_json(spec_json)
    assert spec.formato == "carrossel"
    assert spec.dimensoes == [1080, 1350]
    assert len(spec.slides) == 3  # capa + 2 slides internos
    assert spec.slides[0].template == "capa-carrossel"
    assert spec.slides[1].template == "slide-conteudo"
    assert spec.status == "pending_render"


def test_conteudo_dos_slides_alinha_com_placeholders_do_template() -> None:
    designer, vault = _make_designer()
    pauta = {**_PAUTA_CARROSSEL, "titulo": "Como montar um fluxo"}
    copy = {
        **_COPY,
        "slides": [
            "Slide 1",
            'SLIDE 2 - O PROBLEMA\nTitulo: "X"\nCorpo:\nlinha a\nlinha b',
        ],
    }

    out = designer.execute({"knowledge_pack": _KP, "pauta": pauta, "copy": copy})

    spec_json = vault.read_binary(out.resultado["design_spec_path"]).decode("utf-8")
    spec = DesignSpec.from_json(spec_json)
    # code_pauta agora é slug curto (não o título inteiro — antes duplicava o headline)
    assert spec.slides[0].conteudo["code_pauta"] == "como-montar-um"
    assert spec.slides[0].conteudo["code_formato"] == "carrossel"
    assert spec.slides[1].conteudo["counter"] == "02 / 02"
    # slide string legado vira corpo (via _limpar_texto_slide) na zona s_corpo
    assert spec.slides[1].conteudo["s_corpo"] == "linha a<br>linha b"


def test_slides_estruturados_mapeiam_para_zonas_do_template() -> None:
    designer, vault = _make_designer()
    copy = {
        **_COPY,
        "slides": [
            {"titulo": "capa"},
            {
                "titulo": "O erro nº 1",
                "corpo": "use IA como sistema, não como chat",
                "destaque": "sistema",
                "terminal": "$ comenta AGENTE",
                "label": "salva esse post",
            },
        ],
    }
    out = designer.execute({"knowledge_pack": _KP, "pauta": _PAUTA_CARROSSEL, "copy": copy})

    spec = DesignSpec.from_json(
        vault.read_binary(out.resultado["design_spec_path"]).decode("utf-8")
    )
    c = spec.slides[1].conteudo
    assert c["s_titulo"] == "O erro nº 1"
    assert c["s_corpo"] == "use IA como <b>sistema</b>, não como chat"
    assert 'class="terminal"' in c["terminal_block"]
    assert "$ comenta AGENTE" in c["terminal_block"]
    assert "salva esse post".upper() in c["terminal_block"].upper()


def test_limpar_texto_slide_remove_metadados_de_planejamento() -> None:
    texto = 'SLIDE 3 - VIRADA\nTitulo: "Gancho"\nCorpo:\nvalor final'

    assert _limpar_texto_slide(texto) == "valor final"


def test_post_unico_gera_spec_com_1_slide() -> None:
    designer, vault = _make_designer()
    out = designer.execute(
        {"knowledge_pack": _KP, "pauta": _PAUTA_POST, "copy": {**_COPY, "slides": ["Slide único"]}}
    )
    assert out.sucesso
    spec_json = vault.read_binary(out.resultado["design_spec_path"]).decode("utf-8")
    spec = DesignSpec.from_json(spec_json)
    assert spec.formato == "post-unico"
    assert len(spec.slides) == 1


def test_stories_tem_dimensao_correta() -> None:
    designer, vault = _make_designer()
    out = designer.execute(
        {"knowledge_pack": _KP, "pauta": _PAUTA_STORIES, "copy": {**_COPY, "slides": ["Story"]}}
    )
    assert out.sucesso
    spec_json = vault.read_binary(out.resultado["design_spec_path"]).decode("utf-8")
    spec = DesignSpec.from_json(spec_json)
    assert spec.formato == "stories"
    assert spec.dimensoes == [1080, 1920]


def test_designer_injeta_brief_de_referencia_no_prompt(designer_com_indice) -> None:
    """As fotos/referencias do indice entram no prompt do LLM de decisao."""
    agent, fake_llm = designer_com_indice(
        _INDEX_JSON,
        escolha_yaml=(
            "rota: foto-local\ntemplate_escolhido: capa-foto-split\n"
            "foto_escolhida: IMG_0520.JPG\nsoul_id_prompt: null\n"
            "referencias_usadas: [ref-a.jpeg]\nrationale: ok\n"
        ),
    )
    agent.execute(
        {
            "knowledge_pack": {},
            "pauta": {"tipo": "carrossel", "titulo": "t", "pilar": 1},
            "copy": {"slides": ["s0", "s1"]},
        }
    )
    prompt = fake_llm.calls[0]
    assert "IMG_0520.JPG" in prompt
    assert "1 elemento focal" in prompt


def test_designer_grava_rota_e_referencias_no_resultado(designer_com_indice) -> None:
    agent, _ = designer_com_indice(
        _INDEX_JSON,
        escolha_yaml=(
            "rota: foto-local\ntemplate_escolhido: capa-foto-split\n"
            "foto_escolhida: IMG_0520.JPG\nsoul_id_prompt: null\n"
            "referencias_usadas: [ref-a.jpeg]\nrationale: ok\n"
        ),
    )
    out = agent.execute(
        {
            "knowledge_pack": {},
            "pauta": {"tipo": "carrossel", "titulo": "t", "pilar": 1},
            "copy": {"slides": ["s0", "s1"]},
        }
    )
    assert out.resultado["rota"] == "foto-local"


def test_designer_aceita_rota_foto_higgsfield_com_soul_id_prompt() -> None:
    designer, vault = _make_designer(
        [
            "rota: foto-higgsfield\n"
            "template_escolhido: capa-foto-bg\n"
            "foto_escolhida:\n"
            "soul_id_prompt: Bruno em estudio, luz lateral cinematografica\n"
            "referencias_usadas: [ref-a.jpeg]\n"
            "rationale: precisa de cena gerada\n"
        ]
    )

    out = designer.execute({"knowledge_pack": _KP, "pauta": _PAUTA_CARROSSEL, "copy": _COPY})

    spec_json = vault.read_binary(out.resultado["design_spec_path"]).decode("utf-8")
    spec = DesignSpec.from_json(spec_json)
    assert out.resultado["rota"] == "foto-higgsfield"
    assert spec.slides[0].soul_id_prompt == "Bruno em estudio, luz lateral cinematografica"
    assert spec.slides[0].foto is None


def test_designer_rota_higgsfield_sem_prompt_cai_para_tipografico() -> None:
    designer, vault = _make_designer(
        [
            "rota: foto-higgsfield\n"
            "template_escolhido: capa-foto-bg\n"
            "foto_escolhida:\n"
            "soul_id_prompt: null\n"
            "referencias_usadas: []\n"
            "rationale: invalido\n"
        ]
    )

    out = designer.execute({"knowledge_pack": _KP, "pauta": _PAUTA_CARROSSEL, "copy": _COPY})

    spec_json = vault.read_binary(out.resultado["design_spec_path"]).decode("utf-8")
    spec = DesignSpec.from_json(spec_json)
    assert out.resultado["rota"] == "tipografico"
    assert spec.slides[0].template == "capa-carrossel"
    assert spec.slides[0].soul_id_prompt is None


def test_designer_indice_ausente_nao_quebra(designer_com_indice) -> None:
    """Sem indice (vault sem o arquivo), designer cai no comportamento atual."""
    agent, _ = designer_com_indice(
        None,
        escolha_yaml=(
            "rota: tipografico\ntemplate_escolhido: capa-carrossel\n"
            "foto_escolhida:\nsoul_id_prompt: null\nreferencias_usadas: []\nrationale: ok\n"
        ),
    )
    out = agent.execute(
        {
            "knowledge_pack": {},
            "pauta": {"tipo": "carrossel", "titulo": "t", "pilar": 1},
            "copy": {"slides": ["s0", "s1"]},
        }
    )
    assert out.sucesso is True


def test_designer_variedade_contexto_entra_no_prompt(designer_com_indice) -> None:
    agent, fake_llm = designer_com_indice(
        _INDEX_JSON,
        escolha_yaml=(
            "rota: tipografico\ntemplate_escolhido: capa-carrossel\n"
            "foto_escolhida:\nsoul_id_prompt: null\nreferencias_usadas: []\nrationale: ok\n"
        ),
    )
    agent.execute(
        {
            "knowledge_pack": {},
            "pauta": {"tipo": "carrossel", "titulo": "t", "pilar": 1},
            "copy": {"slides": ["s0", "s1"]},
            "variedade_contexto": ["foto-local", "foto-local"],
        }
    )
    assert "foto-local" in fake_llm.calls[0]


def _designer_com_fotos(escolha_yaml: str, fotos: list[str]) -> tuple[Designer, FakeLLM, list[str]]:
    """Designer cujo vault expõe `fotos` em FotosBruno; router espião registra a complexity."""
    chamadas: list[str] = []
    fake_llm = FakeLLM(responses=[escolha_yaml])

    class _SpyRouter:
        def select(self, complexity: str = "low") -> FakeLLM:
            chamadas.append(complexity)
            return fake_llm

    class _Vault(FakeVault):
        def read_binary(self, path: str) -> bytes:
            raise FileNotFoundError(path)

        def write_binary(self, path: str, dados: bytes) -> None:
            return None

        def list_files_in_folder(self, folder: str, extensions: Any = None) -> list[str]:
            return list(fotos)

    agent = Designer(llm=_SpyRouter(), vault=_Vault())  # type: ignore[arg-type]
    return agent, fake_llm, chamadas


_YAML_TIPO = (
    "rota: tipografico\ntemplate_escolhido: capa-carrossel\n"
    "foto_escolhida:\nsoul_id_prompt: null\nreferencias_usadas: []\nrationale: ok\n"
)


def test_designer_decisao_usa_modelo_high_nao_low() -> None:
    """A decisão de template/rota deve rodar no tier forte (sonnet), não no gemma barato."""
    agent, _, chamadas = _designer_com_fotos(_YAML_TIPO, fotos=[])
    agent.execute(
        {
            "knowledge_pack": {},
            "pauta": {"tipo": "carrossel", "titulo": "t", "pilar": 1},
            "copy": {"slides": ["c", "x"]},
        }
    )
    assert "high" in chamadas
    assert "low" not in chamadas


def test_designer_forca_troca_apos_dois_estilos_iguais_com_foto() -> None:
    agent, fake_llm, _ = _designer_com_fotos(_YAML_TIPO, fotos=["IMG_0520.JPG"])
    agent.execute(
        {
            "knowledge_pack": {},
            "pauta": {"tipo": "carrossel", "titulo": "t", "pilar": 1},
            "copy": {"slides": ["c", "x"]},
            "variedade_contexto": ["tipografico", "tipografico"],
        }
    )
    assert "DIFERENTE" in fake_llm.calls[0]


def test_designer_nao_forca_troca_com_um_estilo_so() -> None:
    agent, fake_llm, _ = _designer_com_fotos(_YAML_TIPO, fotos=["IMG_0520.JPG"])
    agent.execute(
        {
            "knowledge_pack": {},
            "pauta": {"tipo": "carrossel", "titulo": "t", "pilar": 1},
            "copy": {"slides": ["c", "x"]},
            "variedade_contexto": ["tipografico"],
        }
    )
    assert "DIFERENTE" not in fake_llm.calls[0]
