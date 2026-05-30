"""Referencia NotebookLM: manifesto, gate de auth e injecao de grounding."""

from pathlib import Path
from typing import cast

import stella as _pkg
from stella.adapters.llm.base import LLMProvider
from stella.adapters.llm.router import LLMRouter
from stella.agents.agente_marca_mktmagneto.agent import Agent as Coordenador
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
            f"{_BASE}mktmagneto.ia - 01 Spec.md": ("# Spec", {}),
            f"{_BASE}mktmagneto.ia - 03 Briefing do Agente de Conteudo.md": ("briefing", {}),
            f"{_BASE}mktmagneto.ia - 04 Kit de Identidade Visual.md": ("kit", {}),
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
