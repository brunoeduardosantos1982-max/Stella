"""AutoQA — aplica o checklist da marca, refaz 1x, aceita com aviso na 2ª."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

import yaml

from stella.adapters.llm.base import LLMProvider
from stella.domain.post import PostTexto

from .planejador import _strip_code_fence

Veredicto = Literal["aprovado", "refazer", "aceito_com_aviso"]


@dataclass
class ResultadoQA:
    """Resultado da revisão de qualidade."""

    veredicto: Veredicto
    motivo: str = ""
    aviso: str = ""


@dataclass
class AutoQA:
    """Aplica o checklist do briefing à legenda; ciclo: refazer 1x → aceitar com aviso."""

    llm: LLMProvider
    _last_copy_qa: ResultadoQA | None = field(default=None, init=False, repr=False)
    _last_visual_qa: ResultadoQA | None = field(default=None, init=False, repr=False)

    def revisar(
        self,
        post: PostTexto,
        *,
        knowledge: dict[str, str],
        tentativa: int,
    ) -> ResultadoQA:
        resultado = self._avaliar(self._montar_prompt(post, knowledge))

        if resultado.veredicto == "aprovado":
            return resultado

        # refazer na 2ª tentativa → aceito_com_aviso
        if tentativa >= 2:
            return ResultadoQA(
                veredicto="aceito_com_aviso",
                motivo=resultado.motivo,
                aviso=resultado.motivo,
            )
        return resultado

    def aprova_copy(self, *, copy: dict[str, Any], knowledge_pack: dict[str, Any]) -> bool:
        """Retorna True se a copy passou no QA. Armazena resultado em cache."""
        self._last_copy_qa = self._avaliar(self._montar_prompt_copy(copy, knowledge_pack))
        return self._last_copy_qa.veredicto == "aprovado"

    def feedback_copy(self, *, copy: dict[str, Any], knowledge_pack: dict[str, Any]) -> str:
        """Retorna motivo do QA. Reusa cache de aprova_copy quando disponível."""
        if self._last_copy_qa is None:
            self._last_copy_qa = self._avaliar(self._montar_prompt_copy(copy, knowledge_pack))
        if self._last_copy_qa.veredicto == "aprovado":
            return ""
        return self._last_copy_qa.motivo

    def aprova_visual(self, *, copy: dict[str, Any], designer_resultado: dict[str, Any]) -> bool:
        """Retorna True se o visual passou no QA. Armazena resultado em cache."""
        self._last_visual_qa = self._avaliar(self._montar_prompt_visual(copy, designer_resultado))
        return self._last_visual_qa.veredicto == "aprovado"

    def feedback_visual(self, *, copy: dict[str, Any], designer_resultado: dict[str, Any]) -> str:
        """Retorna motivo do QA visual. Reusa cache de aprova_visual quando disponível."""
        if self._last_visual_qa is None:
            self._last_visual_qa = self._avaliar(
                self._montar_prompt_visual(copy, designer_resultado)
            )
        if self._last_visual_qa.veredicto == "aprovado":
            return ""
        return self._last_visual_qa.motivo

    def _avaliar(self, prompt: str) -> ResultadoQA:
        """Chama o LLM e parseia a resposta YAML em ResultadoQA."""
        resposta = self.llm.complete(prompt).texto
        try:
            dados = yaml.safe_load(_strip_code_fence(resposta)) or {}
        except yaml.YAMLError:
            dados = {}
        if not isinstance(dados, dict):
            dados = {}
        if "veredicto" not in dados:
            return ResultadoQA(
                veredicto="aprovado",
                aviso="AutoQA: resposta não parseável; aprovando por default",
            )
        veredicto_raw = str(dados.get("veredicto", "aprovado")).strip().lower()
        motivo = str(dados.get("motivo", ""))
        if veredicto_raw == "aprovado":
            return ResultadoQA(veredicto="aprovado", motivo=motivo)
        return ResultadoQA(veredicto="refazer", motivo=motivo)

    def _montar_prompt_copy(self, copy: dict[str, Any], knowledge_pack: dict[str, Any]) -> str:
        briefing = knowledge_pack.get("briefing", "")
        voz = knowledge_pack.get("voz", "")
        cta = knowledge_pack.get("cta_padrao", "")
        legenda = copy.get("legenda", "")
        hashtags = copy.get("hashtags", [])
        if briefing:
            contexto = f"BRIEFING DA MARCA:\n{briefing}\n\n"
        else:
            contexto = f"VOZ ESPERADA: {voz}\nCTA PADRÃO: {cta}\n\n"
        referencia = knowledge_pack.get("referencia", "")
        if referencia:
            contexto += f"REFERENCIA (principios/exemplos curados):\n{referencia}\n\n"
        return (
            "Aplique a skill `revisao-padroes-marca`.\n\n" + contexto + f"LEGENDA:\n{legenda}\n\n"
            f"HASHTAGS ({len(hashtags)}): {hashtags}\n\n"
            "Devolva APENAS YAML:\n"
            "veredicto: aprovado | refazer\n"
            "motivo: <motivo objetivo>\n"
        )

    def _montar_prompt_visual(
        self, copy: dict[str, Any], designer_resultado: dict[str, Any]
    ) -> str:
        formato = designer_resultado.get("formato", "")
        template_capa = designer_resultado.get("template_capa") or designer_resultado.get(
            "template_escolhido", ""
        )
        slides_planejados = designer_resultado.get("slides_planejados") or designer_resultado.get(
            "slides_renderizados", 0
        )
        legenda = str(copy.get("legenda", ""))
        return (
            "Aplique as skills `composicao-visual-social-2026` e `hierarquia-informacional-feed`.\n\n"
            f"FORMATO: {formato}\n"
            f"TEMPLATE DA CAPA: {template_capa}\n"
            f"SLIDES PLANEJADOS: {slides_planejados}\n"
            f"LEGENDA (completa):\n{legenda}\n\n"
            "Avalie se as escolhas de design são adequadas para o conteúdo.\n"
            "REGRA DE EXTENSÃO: carrosséis de 3 a 5 slides são aceitáveis. NÃO reprove "
            "um carrossel apenas por ter menos de 5 slides — só sinalize se o conteúdo "
            "estiver claramente truncado/incompleto ou a copy cortada.\n\n"
            "Devolva APENAS YAML:\n"
            "veredicto: aprovado | refazer\n"
            "motivo: <motivo objetivo>\n"
        )

    def _montar_prompt(self, post: PostTexto, knowledge: dict[str, str]) -> str:
        briefing = knowledge.get("briefing", "")
        return (
            "Aplique a skill `revisao-padroes-marca` usando o briefing como gabarito.\n\n"
            f"BRIEFING (gabarito da marca):\n{briefing}\n\n"
            f"LEGENDA A REVISAR:\n{post.legenda}\n\n"
            "Devolva APENAS YAML:\n"
            "veredicto: aprovado | refazer\n"
            "motivo: <motivo objetivo>\n"
        )
