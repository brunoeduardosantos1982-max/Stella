"""Agente publicador — publica posts da fila do vault nas redes via Postiz.

Especialista setor=publicacao (NÃO passa por QualityReviewer). Lê posts
prontos da fila (C04 Claude Obsidian/Stella-publicacao/fila/), valida cada um
contra marcas.md e publica via Postiz. Erro num post não derruba os demais.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from typing import Any

from stella.adapters.postiz.base import (
    PostizAgendamento,
    PostizClientProtocol,
    PostizError,
    PostizMidia,
)
from stella.adapters.postiz.client import HttpPostizClient
from stella.adapters.vault.base import Note, VaultRepository
from stella.framework.agent import Agent as BaseAgent
from stella.framework.agent import AgentOutput

_PASTA_BASE = "C04 Claude Obsidian/Stella-publicacao"
_ARQUIVO_MARCAS = f"{_PASTA_BASE}/marcas.md"
_PASTA_FILA = f"{_PASTA_BASE}/fila"
_PADRAO_FILA = f"{_PASTA_FILA}/*.md"
_ENDPOINT_PADRAO = "https://api.postiz.com/public/v1"

# Brasil sem DST desde 2019 — offset fixo evita dependência de `tzdata` no Windows.
_TZ_BRASILIA = timezone(timedelta(hours=-3))
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
    """Especialista setor=publicacao. NÃO passa por QualityReviewer."""

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
        if self._vault is None:
            return AgentOutput(
                resultado={},
                sucesso=False,
                mensagens=["vault não injetado no agente"],
            )
        vault = self._vault

        try:
            postiz = self._obter_cliente(input)
            marcas = self._carregar_marcas(vault)
        except (PostizError, ValueError) as e:
            return AgentOutput(resultado={}, sucesso=False, mensagens=[str(e)])

        publicados: list[str] = []
        erros: list[dict[str, str]] = []
        ignorados = 0

        for nota in vault.scan_recursive(_PADRAO_FILA):
            status = str(nota.frontmatter.get("status", "rascunho"))
            if status not in _STATUS_PUBLICAVEL[modo]:
                ignorados += 1
                continue
            try:
                url = self._publicar_post(nota, marcas, postiz, vault)
                vault.update_frontmatter(
                    nota.path,
                    {"status": "agendado", "post-url": url, "erro": ""},
                )
                publicados.append(nota.path)
            except (
                PostizError,
                ValueError,
                FileNotFoundError,
                KeyError,
                PermissionError,
            ) as e:
                vault.update_frontmatter(nota.path, {"status": "erro", "erro": str(e)})
                erros.append({"post": nota.path, "erro": str(e)})

        mensagens = [
            f"{len(publicados)} post(s) agendado(s), "
            f"{len(erros)} com erro, {ignorados} ignorado(s)."
        ]
        for er in erros:
            mensagens.append(f"  erro em {er['post']}: {er['erro']}")

        return AgentOutput(
            resultado={
                "modo": modo,
                "publicados": publicados,
                "erros": erros,
                "ignorados": ignorados,
            },
            sucesso=len(erros) == 0,
            mensagens=mensagens,
        )

    # ---- helpers internos -------------------------------------------------

    def _obter_cliente(self, input: dict[str, Any]) -> PostizClientProtocol:
        """Devolve o cliente injetado (testes) ou cria um HttpPostizClient
        real a partir do token recebido no input (produção)."""
        if self._postiz is not None:
            return self._postiz
        token = str(input.get("postiz_token", ""))
        if not token:
            raise PostizError("token do Postiz ausente — configure STELLA_POSTIZ_TOKEN no .env")
        self._postiz = HttpPostizClient(token=token, api_base=self._endpoint())
        return self._postiz

    def _endpoint(self) -> str:
        """Endpoint do Postiz declarado na ConexaoMCP injetada (fallback padrão)."""
        for mcp in self._mcps:
            if mcp.nome == "postiz":
                return mcp.endpoint
        return _ENDPOINT_PADRAO

    def _carregar_marcas(self, vault: VaultRepository) -> dict[str, dict[str, str]]:
        """Lê marcas.md e devolve {marca: {plataforma: canal_id}}."""
        if not vault.note_exists(_ARQUIVO_MARCAS):
            raise ValueError(f"arquivo de marcas não encontrado: {_ARQUIVO_MARCAS}")
        nota = vault.read_note(_ARQUIVO_MARCAS)
        bruto = nota.frontmatter.get("marcas")
        if not isinstance(bruto, dict):
            raise ValueError("marcas.md sem a chave 'marcas' (dict) no frontmatter")
        marcas: dict[str, dict[str, str]] = {}
        for marca, canais in bruto.items():
            if not isinstance(canais, dict):
                raise ValueError(f"marca '{marca}' em marcas.md não mapeia plataforma→canal")
            marcas[str(marca)] = {str(p): str(c) for p, c in canais.items()}
        return marcas

    def _publicar_post(
        self,
        nota: Note,
        marcas: dict[str, dict[str, str]],
        postiz: PostizClientProtocol,
        vault: VaultRepository,
    ) -> str:
        """Valida e publica um único post. Devolve as URLs resultantes."""
        fm = nota.frontmatter

        marca = str(fm.get("marca", ""))
        if marca not in marcas:
            raise ValueError(f"marca '{marca}' não está em marcas.md")
        canais = marcas[marca]

        plataformas_raw = fm.get("plataformas")
        if isinstance(plataformas_raw, str):
            plataformas = [plataformas_raw]
        elif isinstance(plataformas_raw, list):
            plataformas = [str(p) for p in plataformas_raw]
        else:
            plataformas = []
        if not plataformas:
            raise ValueError("post sem 'plataformas' no frontmatter")

        agendar_para = fm.get("agendar-para")
        if not agendar_para:
            raise ValueError("post sem 'agendar-para' no frontmatter")
        data_utc = _para_utc_iso(agendar_para)

        conteudo = nota.content.strip()
        if not conteudo:
            raise ValueError("post sem conteúdo (corpo da nota vazio)")

        midias: list[PostizMidia] = []
        imagem = fm.get("imagem")
        if imagem:
            dados = vault.read_binary(f"{_PASTA_FILA}/{imagem}")
            midias.append(postiz.upload_imagem(dados, str(imagem)))

        # Postiz exige settings.post_type ∈ {"post", "story"}. Mapeamos a partir
        # do `tipo-post` do frontmatter (estatico/carrossel → post; story → story).
        tipo_post_raw = str(fm.get("tipo-post", "estatico")).lower().strip()
        post_type = "story" if tipo_post_raw == "story" else "post"

        urls: list[str] = []
        for plataforma in plataformas:
            if plataforma not in canais:
                raise ValueError(f"marca '{marca}' não tem canal para '{plataforma}' em marcas.md")
            resultado = postiz.agendar_post(
                PostizAgendamento(
                    canal_id=canais[plataforma],
                    conteudo=conteudo,
                    data_utc=data_utc,
                    plataforma=plataforma,
                    post_type=post_type,
                    midias=midias,
                )
            )
            if resultado.post_url:
                urls.append(resultado.post_url)
        return " ".join(urls)
