import pytest

from stella.framework.skills_editor import SkillEditor


def test_skill_editor_e_abstrato() -> None:
    with pytest.raises(TypeError):
        SkillEditor()  # type: ignore[abstract]


def test_skill_editor_subclasse_pode_implementar() -> None:
    class _Fake(SkillEditor):
        def __init__(self) -> None:
            self._propostas: dict[str, tuple[str, str, str]] = {}
            self._aplicadas: list[str] = []

        def propose_edit(self, skill_name: str, novo_conteudo: str, justificativa: str) -> str:
            edit_id = f"edit-{len(self._propostas) + 1}"
            self._propostas[edit_id] = (skill_name, novo_conteudo, justificativa)
            return edit_id

        def apply_edit(self, edit_id: str, aprovado_por: str) -> None:
            assert edit_id in self._propostas
            self._aplicadas.append(edit_id)

    ed = _Fake()
    eid = ed.propose_edit("copy-pt-br", "novo conteudo", "ajuste tom")
    assert eid == "edit-1"
    ed.apply_edit(eid, aprovado_por="bruno")
    assert eid in ed._aplicadas
