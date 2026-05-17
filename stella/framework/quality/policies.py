"""ReviewPolicy — decide QUANDO revisar (Q1=C do Design).

Heuristica simples baseada em manifest:
- Coordenadores sempre sao revisados (agregacao importa).
- Setores criticos (design, copy, codigo) sempre revisados.
- Input com chave '--skip-review' truthy pula revisao.
- Caso contrario: especialistas em setores operacionais nao sao revisados
  (revisao tem custo — LLM Sonnet).
"""

from __future__ import annotations

from typing import Any

from stella.framework.manifest import AgentManifest


class ReviewPolicy:
    """Politica de quando aplicar QualityReviewer."""

    SETORES_QA_OBRIGATORIO = frozenset({"design", "copy", "codigo"})

    def deve_revisar(self, manifest: AgentManifest, input_original: dict[str, Any]) -> bool:
        if input_original.get("--skip-review"):
            return False
        if manifest.tipo == "coordenador":
            return True
        if manifest.setor in self.SETORES_QA_OBRIGATORIO:
            return True
        return False
