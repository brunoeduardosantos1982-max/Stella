"""Referencia NotebookLM: manifesto, gate de auth e injecao de grounding."""

from pathlib import Path

import stella as _pkg
from stella.framework.manifest import load_manifest

_BASE = "C04 Claude Obsidian/projetos e specs/mktmagneto.ia/"


def test_manifest_declara_rag_notebooklm():
    manifest_path = (
        Path(_pkg.__file__).parent / "agents" / "agente_marca_mktmagneto" / "manifest.yaml"
    )
    manifest = load_manifest(manifest_path)
    assert manifest.capacidades_externas.rag == "notebooklm"
