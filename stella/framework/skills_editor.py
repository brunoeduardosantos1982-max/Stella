"""HOOK Sub-projeto G — SkillEditor: Stella edita proprias skills.

Implementacao real (proposta + aprovacao + diff + commit no vault) vem no
Sub-projeto G. Aqui apenas o contrato. Garantimos no Design que toda
edicao tem trilha (edit_id, aprovado_por).
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class SkillEditor(ABC):
    """Interface para edicoes de skills propostas pela Stella."""

    @abstractmethod
    def propose_edit(self, skill_name: str, novo_conteudo: str, justificativa: str) -> str:
        """Registra proposta de edicao. Devolve edit_id para tracking."""
        ...

    @abstractmethod
    def apply_edit(self, edit_id: str, aprovado_por: str) -> None:
        """Aplica edicao previamente proposta. Registra quem aprovou."""
        ...
