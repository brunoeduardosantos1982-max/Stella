from dataclasses import dataclass
from datetime import datetime

from stella.adapters.vault.base import VaultRepository


@dataclass
class RegistroInteracao:
    momento: datetime
    usecase: str
    input_usuario: str
    resposta_stella: str


_PASTA_CONVERSAS = "C04 Claude Obsidian/logs e memória/conversas"


class AtualizarMemoria:
    """Anexa interação ao arquivo de conversas do dia.

    Em M2 apenas registra (append). A consolidação inteligente (decidir o que
    entra em Stella Memory.md) fica para M4.
    """

    def __init__(self, vault_repo: VaultRepository) -> None:
        self._vault = vault_repo

    def execute(self, registro: RegistroInteracao) -> None:
        data = registro.momento.strftime("%Y-%m-%d")
        path = f"{_PASTA_CONVERSAS}/{data}.md"
        bloco = self._formatar_bloco(registro)

        if self._vault.note_exists(path):
            nota = self._vault.read_note(path)
            novo_content = nota.content.rstrip() + "\n\n" + bloco
            novo_fm = {**nota.frontmatter, "sessoes": int(nota.frontmatter.get("sessoes", 0)) + 1}
            self._vault.write_note(path, content=novo_content, frontmatter=novo_fm)
        else:
            fm: dict[str, object] = {"data": data, "sessoes": 1}
            self._vault.write_note(path, content=bloco, frontmatter=fm)

    @staticmethod
    def _formatar_bloco(r: RegistroInteracao) -> str:
        hora = r.momento.strftime("%H:%M")
        return (
            f"## {hora} — {r.usecase}\n"
            f"> Bruno: {r.input_usuario}\n"
            f"> Stella: {r.resposta_stella}\n"
        )
