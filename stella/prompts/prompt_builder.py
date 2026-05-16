from dataclasses import dataclass
from pathlib import Path

_PROMPTS_DIR = Path(__file__).parent
_ORDEM_ESTATICA = [
    "identidade.md",
    "tom_jarvis.md",
    "politica_autonomia.md",
    "formato_respostas.md",
]
_TEMPLATE_DINAMICO = "contexto_dinamico.md"


@dataclass
class ContextoDinamico:
    memoria_resumida: str
    tarefas_abertas: str
    projetos_ativos: str
    ultimas_interacoes: str
    saudacao: str


class PromptBuilder:
    """Carrega prompts estáticos (.md) e injeta contexto dinâmico."""

    def __init__(self, prompts_dir: Path | None = None) -> None:
        self._dir = prompts_dir or _PROMPTS_DIR

    def build(self, ctx: ContextoDinamico) -> str:
        partes: list[str] = []
        for nome in _ORDEM_ESTATICA:
            partes.append((self._dir / nome).read_text(encoding="utf-8"))

        dinamico = (self._dir / _TEMPLATE_DINAMICO).read_text(encoding="utf-8")
        dinamico = dinamico.format(
            memoria_resumida=ctx.memoria_resumida,
            tarefas_abertas=ctx.tarefas_abertas,
            projetos_ativos=ctx.projetos_ativos,
            ultimas_interacoes=ctx.ultimas_interacoes,
            saudacao=ctx.saudacao,
        )
        partes.append(dinamico)

        return "\n\n---\n\n".join(partes)

    def saudacao_por_hora(self, hora: int) -> str:
        if 5 <= hora < 12:
            return "Bom dia, Senhor."
        if 12 <= hora < 18:
            return "Boa tarde, Senhor."
        if 18 <= hora < 23:
            return "Boa noite, Senhor."
        return "Senhor."  # madrugada
