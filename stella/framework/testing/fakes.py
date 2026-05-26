"""Fixtures de teste reusaveis para o framework multi-agente.

Todas as Fake* num arquivo so para visibilidade central. Cada Fake implementa
o contrato da ABC correspondente, com estado in-memory para testes rapidos.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from fnmatch import fnmatchcase
from typing import Any

from stella.adapters.llm.base import LLMProvider, LLMResponse, Message
from stella.adapters.vault.base import Note, VaultRepository
from stella.framework.agent import AgentOutput
from stella.framework.client import AgentClient
from stella.framework.errors import AgentNotFoundError
from stella.framework.manifest import AgentManifest, CapacidadesExternas
from stella.framework.rag import RAGClient
from stella.infra.usage_tracker import UsageRecord


class FakeVault(VaultRepository):
    """VaultRepository in-memory.

    Notas sao armazenadas em dict {path: (content, frontmatter, mtime)}.
    `notes` no construtor aceita {path: (content, frontmatter)} para conveniencia
    (mtime e setado automaticamente para datetime.now()).
    """

    def __init__(
        self,
        notes: dict[str, tuple[str, dict[str, Any]]] | None = None,
    ) -> None:
        self._store: dict[str, tuple[str, dict[str, Any], datetime]] = {}
        self._binarios: dict[str, bytes] = {}
        if notes:
            agora = datetime.now()
            for path, (content, fm) in notes.items():
                self._store[path] = (content, dict(fm), agora)

    def read_note(self, path: str) -> Note:
        if path not in self._store:
            raise FileNotFoundError(f"Nota nao encontrada: {path}")
        content, fm, _ = self._store[path]
        return Note(path=path, frontmatter=dict(fm), content=content)

    def write_note(
        self,
        path: str,
        content: str,
        frontmatter: dict[str, Any],
        _mtime: datetime | None = None,
    ) -> None:
        """Argumento `_mtime` e extensao do FakeVault para controlar timestamp
        em testes de scan_recursive(since=...). Producao usa datetime.now()."""
        self._store[path] = (content, dict(frontmatter), _mtime or datetime.now())

    def list_notes_in_folder(self, folder: str) -> list[str]:
        prefixo = folder.rstrip("/") + "/"
        return [p for p in self._store if p.startswith(prefixo) and "/" not in p[len(prefixo) :]]

    def update_frontmatter(self, path: str, updates: dict[str, Any]) -> None:
        if path not in self._store:
            raise FileNotFoundError(f"Nota nao encontrada: {path}")
        content, fm, mtime = self._store[path]
        novo_fm = {**fm, **updates}
        self._store[path] = (content, novo_fm, mtime)

    def note_exists(self, path: str) -> bool:
        return path in self._store

    def read_binary(self, path: str) -> bytes:
        if path not in self._binarios:
            raise FileNotFoundError(f"Arquivo binário não encontrado: {path}")
        return self._binarios[path]

    def write_binary(self, path: str, dados: bytes) -> None:
        """Helper de teste — armazena bytes para read_binary recuperar."""
        self._binarios[path] = dados

    def list_files_in_folder(self, folder: str, extensions: set[str] | None = None) -> list[str]:
        prefixo = folder.rstrip("/") + "/"
        resultado = []
        for path in self._binarios:
            if not path.startswith(prefixo):
                continue
            remainder = path[len(prefixo) :]
            if "/" in remainder:
                continue
            if extensions:
                ext = ("." + remainder.rsplit(".", 1)[-1].lower()) if "." in remainder else ""
                if ext not in extensions:
                    continue
            resultado.append(path)
        return sorted(resultado)

    def scan_recursive(self, pattern: str, since: datetime | None = None) -> list[Note]:
        cutoff = since.timestamp() if since is not None else None
        resultado: list[Note] = []
        for path, (content, fm, mtime) in self._store.items():
            if not _fake_glob_match(path, pattern):
                continue
            if cutoff is not None and mtime.timestamp() < cutoff:
                continue
            resultado.append(Note(path=path, frontmatter=dict(fm), content=content))
        return resultado

    def scoped(self, pattern: str | list[str]) -> VaultRepository:
        from stella.adapters.vault.scoped import ScopedVaultRepository

        return ScopedVaultRepository(self, pattern)


class FakeLLM(LLMProvider):
    """LLMProvider in-memory para testes.

    Construido com lista opcional de respostas. Cada chamada (complete/chat)
    consome a proxima resposta. Sem responses configuradas, devolve texto
    default. Quando responses configuradas esgotam, levanta RuntimeError
    (protege testes de assumir comportamento que nao foi declarado).

    Atributo publico `calls` lista os prompts/messages recebidos (para
    asserts em testes).
    """

    def __init__(self, responses: list[str] | None = None) -> None:
        self._responses = list(responses) if responses else None
        self.calls: list[str] = []

    def _proxima_resposta(self) -> str:
        if self._responses is None:
            return "[FakeLLM] resposta default (sem responses configuradas)"
        if not self._responses:
            raise RuntimeError(
                "FakeLLM esgotou as responses configuradas — adicione mais ou nao configure responses"
            )
        return self._responses.pop(0)

    def complete(self, prompt: str) -> LLMResponse:
        self.calls.append(prompt)
        return LLMResponse(texto=self._proxima_resposta(), tokens_input=10, tokens_output=20)

    def chat(self, messages: list[Message]) -> LLMResponse:
        prompt = "\n".join(f"[{m.role}] {m.content}" for m in messages)
        self.calls.append(prompt)
        return LLMResponse(texto=self._proxima_resposta(), tokens_input=10, tokens_output=20)


@dataclass
class FakeMCP:
    """Conexao MCP fake. Resultados pre-determinados por chave de invocacao."""

    nome: str
    category: str | None = None
    resultados: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    calls: list[str] = field(default_factory=list)

    def invoke(self, chave: str) -> list[dict[str, Any]]:
        self.calls.append(chave)
        return list(self.resultados.get(chave, []))


@dataclass
class FakeRAG(RAGClient):
    """Cliente RAG fake. Busca sempre devolve `docs` pre-determinados.

    FB-M4: herda RAGClient ABC para permitir tipagem estrita no framework.
    """

    docs: list[dict[str, Any]] = field(default_factory=list)
    queries: list[str] = field(default_factory=list)

    def search(self, query: str, k: int = 5) -> list[dict[str, Any]]:
        self.queries.append(query)
        return list(self.docs[:k])


class FakeTracker:
    """UsageTracker fake — registra UsageRecords.

    Satisfaz `stella.framework.tracking.TrackerProtocol` (Protocol estrutural).
    """

    def __init__(self) -> None:
        self.records: list[UsageRecord] = []

    def record(self, record: UsageRecord) -> None:
        self.records.append(record)

    def total_usd(self) -> float:
        return float(sum(r.custo_usd for r in self.records))


class FakeLogger:
    """Logger fake — captura mensagens por nivel em `records`.

    Compativel com a API basica de logging.Logger (info/warning/error/debug),
    suficiente para o framework. Producao usa logging.Logger real.
    """

    def __init__(self) -> None:
        self.records: list[tuple[str, str]] = []

    def debug(self, msg: str, *args: Any) -> None:
        self.records.append(("DEBUG", msg % args if args else msg))

    def info(self, msg: str, *args: Any) -> None:
        self.records.append(("INFO", msg % args if args else msg))

    def warning(self, msg: str, *args: Any) -> None:
        self.records.append(("WARNING", msg % args if args else msg))

    def error(self, msg: str, *args: Any) -> None:
        self.records.append(("ERROR", msg % args if args else msg))


class FakeCopywriter(AgentClient):
    """Especialista fake de copy — AgentClient que retorna outputs pré-determinados.

    Registra payloads recebidos em `self.payloads` para asserts nos testes.
    """

    def __init__(self, outputs: list[dict[str, Any]] | None = None) -> None:
        self._outputs = list(outputs or [])
        self.payloads: list[dict[str, Any]] = []

    def execute(self, payload: dict[str, Any]) -> AgentOutput:
        self.payloads.append(payload)
        if self._outputs:
            resultado = self._outputs.pop(0)
        else:
            resultado = {
                "legenda": "🔥 Hook padrão\n\nContexto\n\n👇 CTA",
                "slides": ["slide 1", "slide 2", "slide 3"],
                "hashtags": ["#ia"] * 12,
                "rationale": "copy padrão FakeCopywriter",
            }
        return AgentOutput(resultado=resultado)

    def manifest(self) -> AgentManifest:
        return AgentManifest(
            nome="copywriter",
            tipo="especialista",
            setor="marketing",
            descricao="fake copywriter para testes",
            execucao="in_process",
            modelo_minimo="gemma",
            inputs_obrigatorios=[],
            exemplo_uso={},
            quando_usar="apenas em testes do framework",
            capacidades_externas=CapacidadesExternas(),
        )


class FakeDesigner(AgentClient):
    """Especialista fake de design — AgentClient que retorna outputs pré-determinados.

    Registra payloads recebidos em `self.payloads` para asserts nos testes.
    """

    def __init__(self, outputs: list[dict[str, Any]] | None = None) -> None:
        self._outputs = list(outputs or [])
        self.payloads: list[dict[str, Any]] = []

    def execute(self, payload: dict[str, Any]) -> AgentOutput:
        self.payloads.append(payload)
        if self._outputs:
            resultado = self._outputs.pop(0)
        else:
            resultado = {
                "png_bytes": b"PNGFAKE-designer",
                "template_escolhido": "capa-carrossel",
                "rationale": "template padrão FakeDesigner",
                "slides_renderizados": 1,
            }
        return AgentOutput(resultado=resultado)

    def manifest(self) -> AgentManifest:
        return AgentManifest(
            nome="designer",
            tipo="especialista",
            setor="marketing",
            descricao="fake designer para testes",
            execucao="in_process",
            modelo_minimo="gemma",
            inputs_obrigatorios=[],
            exemplo_uso={},
            quando_usar="apenas em testes do framework",
            capacidades_externas=CapacidadesExternas(),
        )


class FakeRegistry:
    """Registry fake — resolve agentes por nome via dict de AgentClients.

    Compatível com `delegate_to` (chama `self._registry.get(nome)`).

    Uso:
        registry = FakeRegistry({"copywriter": FakeCopywriter(), "designer": FakeDesigner()})
        agent = Agent(registry=registry)
    """

    def __init__(self, agents: dict[str, AgentClient]) -> None:
        self._agents = agents

    def get(self, nome: str) -> AgentClient:
        if nome not in self._agents:
            raise AgentNotFoundError(
                f"FakeRegistry: agente '{nome}' nao registrado. Conhecidos: {list(self._agents)}"
            )
        return self._agents[nome]


def _fake_glob_match(path: str, pattern: str) -> bool:
    """Match de glob compat com Path.glob — '**' bate qualquer profundidade.

    Replica logica de stella/adapters/vault/scoped.py:_glob_match para que
    FakeVault.scan_recursive funcione sem depender do filesystem real.
    """
    if "**" in pattern:
        sem_double = pattern.replace("**", "*")
        if fnmatchcase(path, sem_double):
            return True
        prefixo = pattern.split("**", 1)[0].rstrip("/")
        sufixo = pattern.split("**", 1)[1].lstrip("/")
        if prefixo and not path.startswith(prefixo):
            return False
        if sufixo and not fnmatchcase(path, f"*{sufixo}"):
            return False
        return True
    return fnmatchcase(path, pattern)
