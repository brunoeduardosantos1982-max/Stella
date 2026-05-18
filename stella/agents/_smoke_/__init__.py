"""_smoke_ — agente interno para smoke test E2E (FB-M4 C2).

Setor 'testes' nao passa por QualityReviewer (politica padrao). Para testar
o fluxo com QualityReviewer, ver _smoke_critico_.
"""

from stella.agents._smoke_.agent import Agent

__all__ = ["Agent"]
