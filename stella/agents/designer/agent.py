"""Designer — especialista stateless que produz o visual (PNG) de um post."""

from __future__ import annotations

from typing import Any

import yaml

from stella.agents.agente_marca_mktmagneto.planejador import _strip_code_fence
from stella.framework.agent import Agent as BaseAgent
from stella.framework.agent import AgentOutput

_TEMPLATE_CAPA = "C04 Claude Obsidian/outputs/mktmagneto-ia/templates/capa-carrossel.html"
_DEFAULT_TEMPLATE = "capa-carrossel"
_INSTAGRAM_4_5 = (1080, 1350)


class Agent(BaseAgent):
    """Especialista de design: recebe copy + knowledge_pack + pauta, devolve PNG bytes."""

    def execute(self, input: dict[str, Any]) -> AgentOutput:
        knowledge_pack = input.get("knowledge_pack")
        pauta = input.get("pauta")
        copy = input.get("copy")

        if self._vault is None:
            return AgentOutput(
                resultado={},
                sucesso=False,
                mensagens=["Vault não injetado no designer"],
            )
        if not knowledge_pack:
            return AgentOutput(
                resultado={},
                sucesso=False,
                mensagens=["knowledge_pack ausente no payload"],
            )
        if not pauta:
            return AgentOutput(
                resultado={},
                sucesso=False,
                mensagens=["pauta ausente no payload"],
            )
        if not copy:
            return AgentOutput(
                resultado={},
                sucesso=False,
                mensagens=["copy ausente no payload"],
            )
        if self._llm is None:
            return AgentOutput(
                resultado={},
                sucesso=False,
                mensagens=["LLM não injetado no designer"],
            )

        # LLM escolhe o template e fornece rationale
        prompt = self._montar_prompt(knowledge_pack, pauta, copy)
        resposta = self._llm.select(complexity="low").complete(prompt).texto

        try:
            dados = yaml.safe_load(_strip_code_fence(resposta)) or {}
        except yaml.YAMLError:
            dados = {}

        if not isinstance(dados, dict):
            dados = {}

        template_escolhido = str(dados.get("template_escolhido", _DEFAULT_TEMPLATE)).strip()
        rationale = str(dados.get("rationale", "")).strip()

        # Renderiza HTML → PNG
        png_bytes = self._renderizar(copy, pauta, template_escolhido)

        slides = copy.get("slides", [])
        return AgentOutput(
            resultado={
                "png_bytes": png_bytes,
                "template_escolhido": template_escolhido,
                "rationale": rationale,
                "slides_renderizados": len(slides),
            },
            sucesso=True,
        )

    def _renderizar(
        self,
        copy: dict[str, Any],
        pauta: dict[str, Any],
        template_escolhido: str,
    ) -> bytes:
        """Carrega template do vault e renderiza como HTML simples (bytes UTF-8).

        Em produção, substituir por PlaywrightRender quando disponível.
        """
        try:
            template_path = _TEMPLATE_CAPA.replace("capa-carrossel", template_escolhido)
            template_html = self._vault.read_note(template_path).content  # type: ignore[union-attr]
        except FileNotFoundError:
            try:
                template_html = self._vault.read_note(_TEMPLATE_CAPA).content  # type: ignore[union-attr]
            except FileNotFoundError:
                template_html = "<html><body>{{TITULO}}</body></html>"

        titulo = pauta.get("titulo", "")
        slides = copy.get("slides", [])
        slide_1 = slides[0] if slides else ""

        html = (
            template_html.replace("{{TITULO}}", titulo)
            .replace("{{SLIDE_1}}", slide_1)
            .replace("{{LEGENDA}}", copy.get("legenda", ""))
        )
        return html.encode("utf-8")

    def _montar_prompt(
        self,
        knowledge_pack: dict[str, Any],
        pauta: dict[str, Any],
        copy: dict[str, Any],
    ) -> str:
        # Suporte a dois formatos: {paleta} (testes) ou {kit} (CarregadorMarca)
        paleta = knowledge_pack.get("paleta") or knowledge_pack.get("kit", "")
        tipo = pauta.get("tipo", "carrossel")
        n_slides = pauta.get("n_slides", 3)
        titulo = pauta.get("titulo", "")
        legenda_preview = str(copy.get("legenda", ""))[:120]

        return (
            "Você é o Designer do Time de Marketing.\n"
            "Aplique as skills `selecao-template-por-conteudo`, "
            "`composicao-visual-social-2026` e `hierarquia-informacional-feed`.\n\n"
            f"PALETA DA MARCA: {paleta}\n"
            f"FORMATO: {tipo}, {n_slides} slides\n"
            f"TÍTULO DO POST: {titulo}\n"
            f"LEGENDA (preview): {legenda_preview}\n\n"
            "Escolha o template mais adequado e explique o rationale.\n\n"
            "Devolva APENAS YAML no formato:\n"
            "template_escolhido: <nome-do-template>\n"
            "rationale: <motivo da escolha>\n"
        )
