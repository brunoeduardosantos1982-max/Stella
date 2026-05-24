"""AutoQA — aplica o checklist da marca, refaz 1x, aceita com aviso na 2ª."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import yaml

from stella.adapters.llm.base import LLMProvider

from .redator import PostTexto

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

    def revisar(
        self,
        post: PostTexto,
        *,
        knowledge: dict[str, str],
        tentativa: int,
    ) -> ResultadoQA:
        prompt = self._montar_prompt(post, knowledge)
        resposta = self.llm.complete(prompt).texto

        try:
            dados = yaml.safe_load(resposta) or {}
        except yaml.YAMLError:
            dados = {}
        if not isinstance(dados, dict):
            dados = {}

        # Fail-open: se não tem chave "veredicto", trata como parse inválido
        if "veredicto" not in dados:
            return ResultadoQA(
                veredicto="aprovado",
                aviso="AutoQA: resposta do LLM não pôde ser parseada (YAML inválido); aprovando por default",
            )

        veredicto_raw = str(dados.get("veredicto", "aprovado")).strip().lower()
        motivo = str(dados.get("motivo", ""))

        if veredicto_raw == "aprovado":
            return ResultadoQA(veredicto="aprovado", motivo=motivo)

        if veredicto_raw == "refazer":
            if tentativa >= 2:
                return ResultadoQA(
                    veredicto="aceito_com_aviso",
                    motivo=motivo,
                    aviso=motivo,
                )
            return ResultadoQA(veredicto="refazer", motivo=motivo)

        # Qualquer outro veredicto inesperado → aprovado por default (fail-open)
        return ResultadoQA(veredicto="aprovado", aviso=f"veredicto desconhecido: {veredicto_raw}")

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
