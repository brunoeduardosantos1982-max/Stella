"""Copywriter — especialista stateless que produz copy para qualquer marca."""

from __future__ import annotations

from typing import Any

import yaml

from stella.agents.agente_marca_mktmagneto.planejador import _strip_code_fence
from stella.framework.agent import Agent as BaseAgent
from stella.framework.agent import AgentOutput

# Campos estruturados de um slide de carrossel. Cada slide vira ZONAS do template
# (titulo grande, corpo, palavra-chave destacada, caixa terminal do CTA, selo).
_SLIDE_CAMPOS = ("titulo", "corpo", "destaque", "terminal", "label")

# Reforço injetado na 2ª tentativa quando o 1º YAML veio inválido/sem legenda.
_REFORCO_FORMATO = (
    "\n\nATENÇÃO: a resposta anterior não veio em YAML válido. Devolva SOMENTE YAML, "
    "sem texto fora dele. Use bloco literal `|` em `corpo` e `terminal` (texto livre com "
    "`:` ou `→` é seguro dentro de `|`) e aspas duplas em `titulo`/`destaque`/`label`/"
    "`headline_hero`. Nunca deixe `: ` solto num valor sem aspas."
)


def _normalizar_slide(bruto: Any) -> dict[str, str]:
    """Normaliza um item de `slides` para dict com as 5 zonas (sempre str).

    Aceita o formato novo (dict estruturado) e o legado (string solta → vira corpo).
    """
    if isinstance(bruto, dict):
        return {c: str(bruto.get(c, "") or "").strip() for c in _SLIDE_CAMPOS}
    return {c: (str(bruto).strip() if c == "corpo" else "") for c in _SLIDE_CAMPOS}


class Agent(BaseAgent):
    """Especialista de copy: recebe knowledge_pack + pauta, devolve copy completa."""

    def execute(self, input: dict[str, Any]) -> AgentOutput:
        knowledge_pack = input.get("knowledge_pack")
        pauta = input.get("pauta")

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
        if self._llm is None:
            return AgentOutput(
                resultado={},
                sucesso=False,
                mensagens=["LLM não injetado no copywriter"],
            )

        prompt = self._montar_prompt(
            knowledge_pack,
            pauta,
            input.get("feedback_anterior"),
            input.get("output_anterior"),
            input.get("briefing"),
        )

        # Robustez: o YAML do LLM falha de vez em quando (':' em texto livre,
        # bloco mal-indentado, resposta vazia transitória). Em vez de perder o
        # post, tenta de novo 1x reforçando o formato estrito.
        dados = self._gerar(prompt)
        if not str(dados.get("legenda", "")).strip():
            dados = self._gerar(prompt + _REFORCO_FORMATO)

        legenda = str(dados.get("legenda", "")).strip()
        slides = [_normalizar_slide(s) for s in dados.get("slides", [])]
        headline_hero = str(dados.get("headline_hero", "")).strip()
        hashtags = [str(h) for h in dados.get("hashtags", [])]
        rationale = str(dados.get("rationale", "")).strip()

        sucesso = bool(legenda)
        return AgentOutput(
            resultado={
                "legenda": legenda,
                "slides": slides,
                "headline_hero": headline_hero,
                "hashtags": hashtags,
                "rationale": rationale,
            },
            sucesso=sucesso,
            mensagens=[] if sucesso else ["LLM não retornou legenda válida (2 tentativas)"],
        )

    def _gerar(self, prompt: str) -> dict[str, Any]:
        """Chama o LLM e parseia o YAML com tolerância (falha → dict vazio)."""
        assert self._llm is not None  # garantido pelo gate em execute
        resposta = self._llm.select(complexity="high").complete(prompt).texto
        try:
            dados = yaml.safe_load(_strip_code_fence(resposta)) or {}
        except yaml.YAMLError:
            dados = {}
        return dados if isinstance(dados, dict) else {}

    def _montar_prompt(
        self,
        knowledge_pack: dict[str, Any],
        pauta: dict[str, Any],
        feedback_anterior: str | None,
        output_anterior: dict[str, Any] | None,
        briefing_copy: dict[str, Any] | None = None,
    ) -> str:
        # Suporte a dois formatos de knowledge_pack:
        # 1. Estruturado (testes unitários): {voz, cta_padrao, hashtags_base}
        # 2. CarregadorMarca (produção): {briefing, spec, kit}
        briefing = knowledge_pack.get("briefing", "")
        voz = knowledge_pack.get("voz", "")
        cta = knowledge_pack.get("cta_padrao", "")
        hashtags_base = knowledge_pack.get("hashtags_base", [])
        pilar = pauta.get("pilar", "")
        titulo = pauta.get("titulo", "")
        tipo = pauta.get("tipo", "carrossel")
        n_slides = pauta.get("n_slides", 3)

        partes = [
            "Você é o Copywriter do Time de Marketing.",
            "Aplique as skills `copywriting-engajamento-ptbr`, `carrossel-instagram-ia` e `estrategia-hashtags`.",
            "",
        ]

        if briefing:
            partes += [f"BRIEFING DA MARCA:\n{briefing}", ""]
        else:
            partes += [
                f"VOZ DA MARCA: {voz}",
                f"CTA PADRÃO: {cta}",
                f"HASHTAGS BASE: {hashtags_base}",
                "",
            ]

        referencia = knowledge_pack.get("referencia", "")
        if referencia:
            partes += [f"REFERENCIA/GROUNDING (use o concreto daqui):\n{referencia}", ""]

        partes += [
            f"PAUTA: pilar {pilar} — {titulo}",
            f"FORMATO: {tipo}, {n_slides} slides",
        ]

        if feedback_anterior:
            output_ant_str = str(output_anterior) if output_anterior else ""
            partes += [
                "",
                "FEEDBACK DO REVISOR (iteração anterior):",
                feedback_anterior,
                "OUTPUT ANTERIOR:",
                output_ant_str,
                "Incorpore o feedback acima na nova versão.",
            ]

        if briefing_copy:
            partes += [
                "",
                "BRIEFING DO DIRETOR (execute exatamente):",
                f"- Angulo: {briefing_copy.get('angulo', '')}",
                f"- Gancho ({briefing_copy.get('gancho_padrao_id', '')}): "
                f"{briefing_copy.get('gancho_instrucao', '')}",
                f"- NOMEIE obrigatoriamente: {briefing_copy.get('pontos_chave', [])}",
                f"- CTA UNICO (use 1 so): {briefing_copy.get('cta_unico', '')}",
                f"- Hashtags sugeridas: {briefing_copy.get('hashtags_sugeridas', [])}",
                "Regras: nomeie o concreto dos pontos-chave; gancho que para o scroll; 1 CTA so.",
                "",
            ]

        partes += [
            "",
            "REGRA DE OURO DOS SLIDES: entregue o TEXTO FINAL pronto pra publicar.",
            "NUNCA escreva rótulos de design ('Headline:', 'Subtexto:', 'Palavra-chave:',",
            "'Caixa terminal:', 'Label oliva:') dentro do texto — esses viram zonas do layout,",
            "preenchidas pelos campos abaixo. `titulo`/`corpo` são frases reais, não instruções.",
            "",
            "Devolva APENAS YAML. Use bloco literal `|` em todo texto livre "
            "(assim `:` e `→` são seguros) e aspas duplas nos campos curtos:",
            'headline_hero: "headline curta e punchy, 2 a 5 palavras (capa de imagem única)"',
            "legenda: |",
            "  🔥 [hook]",
            "",
            "  [corpo]",
            "",
            "  👇 [CTA]",
            "slides:",
            '  - titulo: "frase-título curta, até ~6 palavras"',
            "    corpo: |",
            "      1 a 3 linhas, texto final; pode usar → para itens e : à vontade",
            '    destaque: "palavra/expressão do corpo a realçar (opcional)"',
            "  # o ÚLTIMO slide deve trazer o CTA:",
            "    terminal: |",
            "      $ comando estilo terminal p/ CTA (opcional)",
            '    label: "selo curto, ex SALVA ESSE POST (opcional)"',
            "hashtags:",
            "  - [12 a 15 hashtags]",
            "rationale: [técnica aplicada]",
        ]

        return "\n".join(partes)
