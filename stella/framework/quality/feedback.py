"""FeedbackLogger — anexa correcoes do Bruno em _aprendizados.md (Q3=C).

Quando Bruno diz 'isso nao devia ter passado' (ou similar), a Stella chama
aprender() para registrar a correcao. QualityReviewer le este arquivo na
proxima revisao do mesmo setor.

Formato de cada entrada:

    ### YYYY-MM-DD HH:MM — <setor> — <agente>
    **Correcao:** <texto literal do Bruno>
    **Contexto:** <tarefa onde apareceu>
    **Regra extraida:** <padrao a aplicar>
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from stella.adapters.vault.base import VaultRepository

_PATH = "C04 Claude Obsidian/Padrões/_aprendizados.md"
_FRONTMATTER_INICIAL = {
    "title": "Padrões — aprendizados acumulados da Stella",
    "tipo": "padroes-aprendizados",
    "gerado-por": "FeedbackLogger (FB-M3)",
}


class FeedbackLogger:
    """Acumula correcoes do Bruno em _aprendizados.md."""

    def __init__(self, vault: VaultRepository) -> None:
        self._vault = vault

    def aprender(self, correcao_do_bruno: str, contexto: dict[str, Any]) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        setor = str(contexto.get("setor", "desconhecido"))
        agente = str(contexto.get("agente", "desconhecido"))
        contexto_tarefa = str(contexto.get("contexto_tarefa", "(sem detalhes)"))
        regra = str(contexto.get("regra_extraida", correcao_do_bruno))

        entrada = (
            f"\n### {timestamp} — {setor} — {agente}\n"
            f"**Correcao:** {correcao_do_bruno}\n"
            f"**Contexto:** {contexto_tarefa}\n"
            f"**Regra extraida:** {regra}\n"
        )

        try:
            nota_existente = self._vault.read_note(_PATH)
            novo_content = nota_existente.content.rstrip() + "\n" + entrada
            self._vault.write_note(_PATH, novo_content, nota_existente.frontmatter)
        except FileNotFoundError:
            self._vault.write_note(_PATH, entrada, dict(_FRONTMATTER_INICIAL))
