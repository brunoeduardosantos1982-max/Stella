"""Agente publicador — publica posts da fila do vault nas redes via Postiz.

Especialista setor=publicacao (NÃO passa por QualityReviewer). Esta é a
versão mínima (scaffolding); a lógica de fila chega na Task 8.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from typing import Any

from stella.adapters.postiz.base import PostizClientProtocol
from stella.framework.agent import Agent as BaseAgent
from stella.framework.agent import AgentOutput

_PASTA_BASE = "C04 Claude Obsidian/Stella-publicacao"
_ARQUIVO_MARCAS = f"{_PASTA_BASE}/marcas.md"
_PASTA_FILA = f"{_PASTA_BASE}/fila"
_PADRAO_FILA = f"{_PASTA_FILA}/*.md"

_TZ_BRASILIA = timezone(timedelta(hours=-3))  # UTC-3 (padrão)
_TZ_UTC = UTC

# Status que cada modo está autorizado a publicar.
_STATUS_PUBLICAVEL: dict[str, set[str]] = {
    "semi-auto": {"aprovado"},
    "auto": {"aprovado", "rascunho"},
}


def _para_utc_iso(valor: object) -> str:
    """Converte 'agendar-para' (horário de Brasília) para ISO 8601 UTC.

    Aceita str ('AAAA-MM-DD HH:MM') ou datetime — YAML pode parsear o campo
    como qualquer um dos dois.
    """
    if isinstance(valor, datetime):
        dt = valor
    elif isinstance(valor, str):
        try:
            dt = datetime.strptime(valor.strip(), "%Y-%m-%d %H:%M")
        except ValueError as e:
            raise ValueError(f"'agendar-para' inválido: '{valor}' (use 'AAAA-MM-DD HH:MM')") from e
    else:
        raise ValueError(f"'agendar-para' com tipo inesperado: {type(valor).__name__}")
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_TZ_BRASILIA)
    return dt.astimezone(_TZ_UTC).strftime("%Y-%m-%dT%H:%M:%S.000Z")


class Agent(BaseAgent):
    """Especialista setor=publicacao. NÃO passa por QualityReviewer.

    Lê posts prontos da fila, valida cada um contra marcas.md e publica via
    Postiz. Erro num post não derruba os demais.
    """

    def __init__(
        self,
        *,
        postiz_client: PostizClientProtocol | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._postiz = postiz_client

    def execute(self, input: dict[str, Any]) -> AgentOutput:
        modo = str(input.get("modo", "semi-auto"))
        if modo not in _STATUS_PUBLICAVEL:
            return AgentOutput(
                resultado={},
                sucesso=False,
                mensagens=[f"modo de publicação inválido: '{modo}'"],
            )
        return AgentOutput(
            resultado={"modo": modo, "publicados": [], "erros": [], "ignorados": 0},
            sucesso=True,
            mensagens=["0 post(s) agendado(s), 0 com erro, 0 ignorado(s)."],
        )
