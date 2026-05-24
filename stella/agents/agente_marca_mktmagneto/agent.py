"""Agente de Marca @mktmagneto.ia — orquestrador do pipeline semanal.

AM-M2 Task 13: pipeline de texto end-to-end (sem visual/fila).
Encadeia CarregadorMarca → Pesquisador → Planejador → Redator.

Próximos:
- AM-M3 Task 16-17: MontadorVisual (HTML → PNG via Playwright)
- AM-M4 Task 18-20: AutoQA + EscritorFila + wire final + calendário
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, cast

from stella.framework.agent import Agent as BaseAgent
from stella.framework.agent import AgentOutput

from .autoqa import AutoQA
from .carregador_marca import CarregadorMarca
from .escritor_fila import EscritorFila
from .montador_visual import MontadorVisual, RenderProtocol
from .pesquisador import Pesquisador, _MCPInvocavel
from .planejador import Planejador
from .redator import PostTexto, Redator

_BRT = timezone(timedelta(hours=-3))

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

    def _now(self) -> datetime:
        """Retorna o horário atual em BRT. Pode ser sobrescrito para testes."""
        return datetime.now(_BRT)

    def _proximas_3_datas(self, agora: datetime) -> list[datetime]:
        """3 datas: próximas Segunda/Quarta/Sexta às 09:00 BRT, após `agora`."""
        candidatos: list[datetime] = []
        for i in range(1, 14):  # janela de 2 semanas
            d = (agora + timedelta(days=i)).date()
            if d.weekday() in (0, 2, 4):  # 0=seg, 2=qua, 4=sex
                candidatos.append(datetime(d.year, d.month, d.day, 9, 0, tzinfo=_BRT))
                if len(candidatos) == 3:
                    break
        return candidatos

    def _atualizar_calendario(self, pautas: list[Any], datas: list[datetime]) -> None:
        """Acrescenta as 3 pautas planejadas ao calendário em outputs/mktmagneto-ia/calendario.md."""
        if self._vault is None:
            return
        cal_path = "C04 Claude Obsidian/outputs/mktmagneto-ia/calendario.md"
        header = (
            "# Calendário de pautas — @mktmagneto.ia\n\n"
            "| data | pilar | título | status |\n"
            "|------|-------|--------|--------|\n"
        )
        linhas_novas = "\n".join(
            f"| {d.strftime('%Y-%m-%d')} | {p.pilar} | {p.titulo} | planejado |"
            for p, d in zip(pautas, datas, strict=False)
        )
        try:
            nota = self._vault.read_note(cal_path)
            conteudo = nota.content.rstrip() + "\n" + linhas_novas + "\n"
        except FileNotFoundError:
            conteudo = header + linhas_novas + "\n"
        self._vault.write_note(cal_path, conteudo, {})

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

        # 7. AutoQA + EscritorFila — Task 20
        agora = self._now()
        datas = self._proximas_3_datas(agora)
        autoqa = AutoQA(llm=self._llm.select(complexity="high"))
        escritor = EscritorFila(vault=self._vault)
        redator = Redator(llm=self._llm.select(complexity="high"))  # reusar da etapa 5
        notas_escritas: list[str] = []
        posts_em_rascunho = 0

        for i, post in enumerate(posts):
            # AutoQA — tentativa 1
            resultado = autoqa.revisar(post, knowledge=knowledge, tentativa=1)
            if resultado.veredicto == "refazer":
                # refazer e revisar de novo
                try:
                    post = redator.escrever(pauta=pautas[i], knowledge=knowledge)
                except Exception as e:  # noqa: BLE001
                    erros.append(f"Refazer post {i+1} falhou: {e}")
                    continue
                resultado = autoqa.revisar(post, knowledge=knowledge, tentativa=2)

            if resultado.veredicto in ("aprovado", "aceito_com_aviso"):
                post_id = datas[i].strftime("%Y-%m-%d") + f"-{i+1:02d}"
                # Regerar PNG com post_id correto (contém a data)
                try:
                    png = montador.montar(post, post_id=post_id)
                except Exception as e:  # noqa: BLE001
                    erros.append(f"Visual de '{post.titulo}' falhou na escrita final: {e}")
                    continue
                try:
                    path = escritor.escrever(
                        post, post_id=post_id, png_bytes=png, agendar_para=datas[i]
                    )
                    notas_escritas.append(path)
                    posts_em_rascunho += 1
                except Exception as e:  # noqa: BLE001
                    erros.append(f"Escrita do post {i+1} falhou: {e}")
            if resultado.aviso:
                erros.append(f"Post {i+1} aviso QA: {resultado.aviso}")

        # 8. Calendário (criar/atualizar) — Task 20
        self._atualizar_calendario(pautas[:posts_em_rascunho], datas[:posts_em_rascunho])

        msgs = erros + [
            f"{len(posts)} post(s) com texto pronto, "
            f"{len(imagens)} visual(is) renderizado(s), "
            f"{posts_em_rascunho} post(s) em rascunho na fila."
        ]
        return AgentOutput(
            resultado={
                "posts_textos": posts,
                "pautas": pautas,
                "digest": digest,
                "imagens": imagens,
                "posts_em_rascunho": posts_em_rascunho,
            },
            sucesso=bool(posts),
            mensagens=msgs,
        )
