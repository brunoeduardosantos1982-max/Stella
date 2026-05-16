from dataclasses import dataclass, field

from stella.adapters.llm.base import LLMProvider, Message
from stella.adapters.vault.base import VaultRepository
from stella.usecases.base import EntradaInvalida

_PASTA_PROJETOS = "B01 Projetos"

_SYSTEM_QA = (
    "Você é a Stella, assistente pessoal do Bruno. Responda em português brasileiro, "
    "direto e conciso, no formato:\n"
    "1. **TL;DR** em 1 frase\n"
    "2. **Detalhe** em tabela ou lista (3-7 itens)\n"
    "3. **Próxima ação sugerida** (1 linha)\n"
    "4. **Fontes**: wikilinks consultados\n"
    "Use wikilinks Obsidian (ex: [[Centro Viagens]]) ao citar a nota fonte."
)


@dataclass
class EntradaPergunta:
    pergunta: str
    projeto: str


@dataclass
class ResultadoResposta:
    resposta: str
    fontes: list[str] = field(default_factory=list)


class ResponderProjeto:
    """Capacidade 2 — responde pergunta sobre projeto lendo nota correspondente em B01."""

    def __init__(self, llm: LLMProvider, vault_repo: VaultRepository) -> None:
        self._llm = llm
        self._vault = vault_repo

    def execute(self, entrada: EntradaPergunta) -> ResultadoResposta:
        pergunta = entrada.pergunta.strip()
        if not pergunta:
            raise EntradaInvalida("pergunta não pode estar vazia")

        path = f"{_PASTA_PROJETOS}/{entrada.projeto}.md"
        if not self._vault.note_exists(path):
            raise EntradaInvalida(
                f"projeto '{entrada.projeto}' não encontrado em {_PASTA_PROJETOS}/"
            )

        nota = self._vault.read_note(path)
        contexto = (
            f"Projeto: [[{entrada.projeto}]]\n"
            f"Conteúdo da nota:\n---\n{nota.content}\n---\n\n"
            f"Pergunta: {pergunta}"
        )
        resp = self._llm.chat(
            [
                Message(role="system", content=_SYSTEM_QA),
                Message(role="user", content=contexto),
            ]
        )
        return ResultadoResposta(resposta=resp.texto, fontes=[path])
