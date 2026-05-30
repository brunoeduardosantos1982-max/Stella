"""Agente de Marca @mktmagneto.ia — coordenador do Time de Marketing.

v2 (Sub-projeto C): delega copy para o especialista `copywriter` e
visual para o especialista `designer`. Mantém: pesquisa, planejamento,
AutoQA e gravação na fila do publicador.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, cast

from stella.framework.agent import Agent as BaseAgent
from stella.framework.agent import AgentOutput

from .autoqa import AutoQA
from .carregador_marca import CarregadorMarca
from .escritor_fila import EscritorFila
from .pesquisador import Pesquisador, _MCPInvocavel
from .planejador import Planejador
from .redator import PostTexto

_BRT = timezone(timedelta(hours=-3))
_PILARES = [1, 2, 3, 4]

# Nicho da marca — âncora obrigatória das queries de pesquisa. Sem isso, o
# Pesquisador buscava "pilar 1 tendências 2026" (vazio de sentido) e o digest
# vinha contaminado com temas fora do nicho (decoração/Japandi).
_NICHO = "IA aplicada a marketing e vendas"
# Seeds de pesquisa por pilar. Pilar 4 (build-in-public) é produzido pelo Bruno
# — fora da pesquisa automatizada.
_PILAR_QUERIES: dict[int, str] = {
    1: "mitos e erros ao adotar IA em negócios",
    2: "ferramentas e prompts de IA para marketing",
    3: "agentes de IA e automação para marketing e vendas",
}


def _queries_pesquisa() -> list[str]:
    """Queries de pesquisa ancoradas no nicho da marca (uma por pilar 1–3)."""
    return [f"{_NICHO}: {seed}" for seed in _PILAR_QUERIES.values()]


class Agent(BaseAgent):
    """Coordenador que orquestra o lote semanal de 3 posts.

    Pipeline: Pesquisador → Planejador → (copywriter → AutoQA) ×3 →
              (designer → AutoQA) ×3 → EscritorFila → calendário.
    """

    def _now(self) -> datetime:
        return datetime.now(_BRT)

    def _proximas_3_datas(self, agora: datetime) -> list[datetime]:
        candidatos: list[datetime] = []
        for i in range(1, 14):
            d = (agora + timedelta(days=i)).date()
            if d.weekday() in (0, 2, 4):
                candidatos.append(datetime(d.year, d.month, d.day, 9, 0, tzinfo=_BRT))
                if len(candidatos) == 3:
                    break
        return candidatos

    def _atualizar_calendario(self, pautas: list[Any], datas: list[datetime]) -> None:
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

    def execute(self, input: dict[str, Any]) -> AgentOutput:  # noqa: A002
        if self._vault is None or self._llm is None or self._registry is None:
            return AgentOutput(
                resultado={},
                sucesso=False,
                mensagens=["Vault, LLM ou registry não injetado — não posso rodar."],
            )

        # 0. Gate de auth do NotebookLM - referencia e grounding obrigatorio.
        if self._rag is not None and hasattr(self._rag, "auth_check"):
            if not self._rag.auth_check():
                return AgentOutput(
                    resultado={},
                    sucesso=False,
                    mensagens=[
                        "Senhor, NotebookLM deslogou. Rode `notebooklm login` e me chame de novo."
                    ],
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

        # 2. Pesquisa em cascata — queries ancoradas no nicho da marca
        research_mcps = [m for m in self._mcps if getattr(m, "category", None) == "research"]
        digest = Pesquisador(research_mcps=cast(list[_MCPInvocavel], research_mcps)).pesquisar(
            pilares=_queries_pesquisa()
        )

        # 3. Planejamento (3 pautas) — briefing injetado para ancorar no nicho
        pautas = Planejador(llm=self._llm.select(complexity="high")).planejar(
            pilares_briefing=_PILARES,
            digest=digest,
            calendario_atual=[],
            briefing=knowledge.get("briefing", ""),
        )

        # 4. Pipeline por pauta: copy → QA → design → QA → fila
        agora = self._now()
        datas = self._proximas_3_datas(agora)
        autoqa = AutoQA(llm=self._llm.select(complexity="high"))
        escritor = EscritorFila(vault=self._vault)
        erros: list[str] = []
        posts_em_rascunho = 0

        for i, pauta in enumerate(pautas):
            post_warnings: list[str] = []
            pauta_dict: dict[str, Any] = {
                "pilar": pauta.pilar,
                "titulo": pauta.titulo,
                "tipo": "carrossel",
                "n_slides": 3,
            }

            # Grounding obrigatorio por pauta: consulta o notebook de referencia.
            referencia_txt = ""
            if self._rag is not None:
                docs = self._rag.search(pauta.titulo)
                referencia_txt = "\n\n".join(str(d.get("texto", "")) for d in docs)
            knowledge_pauta = {**knowledge, "referencia": referencia_txt}

            # Copy — tentativa 1
            copy_out = self.delegate_to(
                "copywriter", {"knowledge_pack": knowledge_pauta, "pauta": pauta_dict}
            )
            if not copy_out.sucesso:
                erros.append(f"Post {i + 1}: copywriter falhou — {copy_out.mensagens}")
                continue
            copy = copy_out.resultado

            # QA copy — retry com feedback se reprovado
            if not autoqa.aprova_copy(copy=copy, knowledge_pack=knowledge_pauta):
                feedback_c = autoqa.feedback_copy(copy=copy, knowledge_pack=knowledge_pauta)
                copy_out2 = self.delegate_to(
                    "copywriter",
                    {
                        "knowledge_pack": knowledge_pauta,
                        "pauta": pauta_dict,
                        "feedback_anterior": feedback_c,
                        "output_anterior": copy,
                    },
                )
                copy = copy_out2.resultado if copy_out2.sucesso else copy
                if not autoqa.aprova_copy(copy=copy, knowledge_pack=knowledge_pauta):
                    aviso = autoqa.feedback_copy(copy=copy, knowledge_pack=knowledge_pauta)
                    msg = f"Post {i + 1} copy QA aviso: {aviso}"
                    erros.append(msg)
                    post_warnings.append(msg)

            # Design
            design_out = self.delegate_to(
                "designer", {"knowledge_pack": knowledge_pauta, "pauta": pauta_dict, "copy": copy}
            )
            if not design_out.sucesso:
                erros.append(f"Post {i + 1}: designer falhou — {design_out.mensagens}")
                continue
            designer_resultado = design_out.resultado

            # QA visual — apenas aviso, nunca bloqueia
            if not autoqa.aprova_visual(copy=copy, designer_resultado=designer_resultado):
                aviso_v = autoqa.feedback_visual(copy=copy, designer_resultado=designer_resultado)
                msg = f"Post {i + 1} visual QA aviso: {aviso_v}"
                erros.append(msg)
                post_warnings.append(msg)

            # Gravar na fila
            post_id = datas[i].strftime("%Y-%m-%d") + f"-{i + 1:02d}"
            post = PostTexto(
                pilar=pauta.pilar,
                titulo=pauta.titulo,
                legenda=copy.get("legenda", ""),
                hashtags=copy.get("hashtags", []),
                slides=copy.get("slides", []),
            )
            try:
                design_spec_path: str = designer_resultado.get("design_spec_path", "")
                status = "needs_review" if post_warnings else "pending_render"
                escritor.escrever(
                    post,
                    post_id=post_id,
                    design_spec_path=design_spec_path,
                    agendar_para=datas[i],
                    status=status,
                    qa_warnings=post_warnings,
                )
                posts_em_rascunho += 1
            except Exception as e:  # noqa: BLE001
                erros.append(f"Escrita do post {i + 1} falhou: {e}")

        self._atualizar_calendario(pautas[:posts_em_rascunho], datas[:posts_em_rascunho])

        return AgentOutput(
            resultado={
                "posts_em_rascunho": posts_em_rascunho,
                "pautas": pautas,
                "digest": digest,
            },
            sucesso=bool(posts_em_rascunho),
            mensagens=erros + [f"{posts_em_rascunho} post(s) em rascunho na fila."],
        )
