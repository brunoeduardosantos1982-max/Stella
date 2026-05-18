"""_smoke_critico_ — variante setor=copy do _smoke_ (FB-M4 C2).

Setor 'copy' aciona QualityReviewer por padrao (ReviewPolicy.deve_revisar).
Usado pelo smoke test E2E para validar loop completo: agente -> LLM -> QualityReviewer.
"""

from stella.agents._smoke_critico_.agent import Agent

__all__ = ["Agent"]
