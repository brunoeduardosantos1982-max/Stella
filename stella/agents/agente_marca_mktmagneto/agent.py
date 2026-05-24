"""Agente de Marca @mktmagneto.ia — orquestrador do pipeline semanal.

AM-M2 Task 13: pipeline de texto end-to-end (sem visual/fila).
Encadeia CarregadorMarca → Pesquisador → Planejador → Redator.

Próximos:
- AM-M3 Task 16-17: MontadorVisual (HTML → PNG via Playwright)
- AM-M4 Task 18-20: AutoQA + EscritorFila + wire final + calendário
"""

from __future__ import annotations

from typing import Any, cast

from stella.framework.agent import Agent as BaseAgent
from stella.framework.agent import AgentOutput

from .carregador_marca import CarregadorMarca
from .montador_visual import MontadorVisual, RenderProtocol
from .pesquisador import Pesquisador, _MCPInvocavel
from .planejador import Planejador
from .redator import PostTexto, Redator

# Pilares do @mktmagneto.ia — vêm do spec (4 pilares: Despertar, Ferramentas,
# Agentes/Automação, Build-in-public). Tratados como inteiros 1-4 nesta versão.
_PILARES = [1, 2, 3, 4]


class Agent(BaseAgent):
    """Especialista que produz o lote semanal de 3 posts em rascunho.

    v1 (AM-M1..M4): faz pesquisa, planejamento, redação e (futuro) visual
    diretamente. Quando o Sub-projeto C (Time de Marketing) existir, este
    agente vira coordenador.
    """

    def _get_render(self) -> RenderProtocol:
        """Devolve o render injetado (`self._render` se setado) ou cria PlaywrightRender."""
        existing: Any = getattr(self, "_render", None)
        if existing is not None:
            return cast(RenderProtocol, existing)
        from stella.adapters.render.playwright_render import PlaywrightRender

        return PlaywrightRender()

    def execute(self, input: dict[str, Any]) -> AgentOutput:
        if self._vault is None or self._llm is None:
            return AgentOutput(
                resultado={},
                sucesso=False,
                mensagens=["Vault ou LLM não injetado — não posso rodar."],
            )

        # 1. Conhecimento da marca
        try:
            knowledge = CarregadorMarca(vault=self._vault).carregar()
        except FileNotFoundError as e:
            return AgentOutput(
                resultado={},
                sucesso=False,
                mensagens=[f"Doc da marca ausente: {e}"],
            )

        # 2. Pesquisa em cascata (Brave → Perplexity)
        research_mcps = [m for m in self._mcps if getattr(m, "category", None) == "research"]
        digest = Pesquisador(research_mcps=cast(list[_MCPInvocavel], research_mcps)).pesquisar(
            pilares=[f"pilar {p}" for p in _PILARES]
        )

        # 3. Calendário atual (vazio na v1; persistência virá na Task 20)
        calendario: list[dict[str, Any]] = []

        # 4. Planejamento (3 pautas)
        pautas = Planejador(llm=self._llm.select(complexity="high")).planejar(
            pilares_briefing=_PILARES,
            digest=digest,
            calendario_atual=calendario,
        )

        # 5. Redação (1 post por pauta) — isolado em try/except por post
        redator = Redator(llm=self._llm.select(complexity="high"))
        posts: list[PostTexto] = []
        erros: list[str] = []
        for pauta in pautas:
            try:
                posts.append(redator.escrever(pauta=pauta, knowledge=knowledge))
            except Exception as e:  # noqa: BLE001 — isolado por post
                erros.append(f"Pauta '{pauta.titulo}' falhou na redação: {e}")

        # 6. Montagem visual (HTML → PNG) — Task 17
        render = self._get_render()
        montador = MontadorVisual(vault=self._vault, render=render)
        imagens: dict[str, bytes] = {}
        for i, post in enumerate(posts, start=1):
            post_id = f"post-{i:02d}"  # convenção temporária; data real virá na Task 20
            try:
                imagens[post_id] = montador.montar(post, post_id=post_id)
            except Exception as e:  # noqa: BLE001 — isolado por post
                erros.append(f"Post '{post.titulo}' falhou no visual: {e}")

        msgs = erros + [
            f"{len(posts)} post(s) com texto pronto, "
            f"{len(imagens)} visual(is) renderizado(s) "
            f"(fila e automação virão nos próximos milestones)."
        ]
        return AgentOutput(
            resultado={
                "posts_textos": posts,
                "pautas": pautas,
                "digest": digest,
                "imagens": imagens,
            },
            sucesso=bool(posts),
            mensagens=msgs,
        )
