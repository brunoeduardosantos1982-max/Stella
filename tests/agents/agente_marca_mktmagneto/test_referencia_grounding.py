"""Referencia NotebookLM: manifesto, gate de auth e injecao de grounding."""

from pathlib import Path
from typing import cast

import stella as _pkg
from stella.adapters.llm.base import LLMProvider
from stella.adapters.llm.router import LLMRouter
from stella.agents.agente_marca_mktmagneto.agent import Agent as Coordenador
from stella.agents.agente_marca_mktmagneto.carregador_marca import _DOCS_DA_MARCA
from stella.framework.manifest import load_manifest
from stella.framework.testing.fakes import (
    FakeCopywriter,
    FakeDesigner,
    FakeLLM,
    FakeNotebookLMRAG,
    FakeRegistry,
    FakeVault,
)

_BASE = "C04 Claude Obsidian/projetos e specs/mktmagneto.ia/"


def test_manifest_declara_rag_notebooklm():
    manifest_path = (
        Path(_pkg.__file__).parent / "agents" / "agente_marca_mktmagneto" / "manifest.yaml"
    )
    manifest = load_manifest(manifest_path)
    assert manifest.capacidades_externas.rag == "notebooklm"


class _FakeRouter:
    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    def select(self, complexity: str) -> LLMProvider:
        return self._llm


def _vault() -> FakeVault:
    return FakeVault(
        {
            _DOCS_DA_MARCA["spec"]: ("# Spec", {}),
            _DOCS_DA_MARCA["briefing"]: ("briefing", {}),
            _DOCS_DA_MARCA["kit"]: ("kit", {}),
        }
    )


def _coord(rag: FakeNotebookLMRAG, vault: FakeVault, coord_llm: FakeLLM) -> Coordenador:
    registry = FakeRegistry({"copywriter": FakeCopywriter(), "designer": FakeDesigner()})
    return Coordenador(
        vault=vault,
        llm=cast(LLMRouter, _FakeRouter(coord_llm)),
        mcps=[],
        rag=rag,
        registry=registry,
    )


def test_auth_caido_para_e_nao_produz(monkeypatch):
    vault = _vault()
    rag = FakeNotebookLMRAG(autenticado=False)
    coord = _coord(rag, vault, FakeLLM())

    out = coord.execute({})

    assert out.sucesso is False
    assert any("notebooklm login" in m for m in out.mensagens)
    # nenhuma nota escrita na fila
    fila = [p for p in vault._store if "Stella-publicacao/fila/" in p]
    assert fila == []


def test_grounding_injetado_no_payload_do_copywriter(monkeypatch):
    vault = _vault()
    rag = FakeNotebookLMRAG(
        autenticado=True,
        docs=[{"texto": "Use prova concreta no gancho.", "citacoes": []}],
    )
    registry = FakeRegistry({"copywriter": FakeCopywriter(), "designer": FakeDesigner()})
    # plan com 1 pauta + QA aprovado (copy + visual)
    coord_llm = FakeLLM(
        responses=[
            'pautas:\n  - {pilar: 1, titulo: "do chat a construcao"}\n',
            "atribuicoes:\n  - rota: tipografico\n    tema:\n    gancho_padrao_id: mito-verdade\n",
            "angulo: a\ngancho_padrao_id: mito-verdade\ncta_unico: C\n",
            "veredicto: aprovado\nmotivo: ok",
            "veredicto: aprovado\nmotivo: ok",
        ]
    )
    coord = Coordenador(
        vault=vault,
        llm=cast(LLMRouter, _FakeRouter(coord_llm)),
        mcps=[],
        rag=rag,
        registry=registry,
    )

    coord.execute({})

    # a query de grounding usou o titulo da pauta
    assert any("do chat a construcao" in q for q in rag.queries)
    # o copywriter recebeu o knowledge_pack com a chave 'referencia' preenchida
    copyw = cast(FakeCopywriter, registry.get("copywriter"))
    assert copyw.payloads, "copywriter deveria ter sido chamado"
    kp = copyw.payloads[0]["knowledge_pack"]
    assert "prova concreta" in kp.get("referencia", "")
