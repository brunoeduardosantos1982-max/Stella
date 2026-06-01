"""DiretorCriativo - atribui formato+tema+gancho ao lote forcando variedade."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import yaml

from stella.adapters.llm.base import LLMProvider
from stella.agents.agente_marca_mktmagneto.planejador import Pauta, _strip_code_fence

_ROTAS = ("tipografico", "foto-local", "foto-hero")


@dataclass
class AtribuicaoEditorial:
    pilar: int
    titulo: str
    rota: str
    tema: str | None
    gancho_padrao_id: str


@dataclass
class DiretorCriativo:
    llm: LLMProvider
    temas_disponiveis: list[str]

    def dirigir(
        self, *, pautas: list[Pauta], knowledge: dict[str, Any], digest: str
    ) -> list[AtribuicaoEditorial]:
        dados = self._chamar(pautas, knowledge, digest)
        atribuicoes = self._parsear(pautas, dados)
        return self._forcar_variedade(atribuicoes)

    def _chamar(
        self, pautas: list[Pauta], knowledge: dict[str, Any], digest: str
    ) -> dict[str, Any]:
        prompt = self._prompt(pautas, knowledge, digest)
        try:
            dados = yaml.safe_load(_strip_code_fence(self.llm.complete(prompt).texto)) or {}
        except yaml.YAMLError:
            dados = {}
        return dados if isinstance(dados, dict) else {}

    def _parsear(self, pautas: list[Pauta], dados: dict[str, Any]) -> list[AtribuicaoEditorial]:
        raw = dados.get("atribuicoes", []) if isinstance(dados, dict) else []
        out: list[AtribuicaoEditorial] = []
        for i, pauta in enumerate(pautas):
            item = raw[i] if i < len(raw) and isinstance(raw[i], dict) else {}
            rota = str(item.get("rota", "tipografico")).strip()
            if rota not in _ROTAS:
                rota = "tipografico"
            tema = str(item.get("tema") or "").strip() or None
            if rota == "foto-hero" and tema not in self.temas_disponiveis:
                rota, tema = "tipografico", None
            if rota != "foto-hero":
                tema = None
            out.append(
                AtribuicaoEditorial(
                    pilar=pauta.pilar,
                    titulo=pauta.titulo,
                    rota=rota,
                    tema=tema,
                    gancho_padrao_id=str(item.get("gancho_padrao_id", "")),
                )
            )
        return out

    def _forcar_variedade(
        self, atribuicoes: list[AtribuicaoEditorial]
    ) -> list[AtribuicaoEditorial]:
        if not atribuicoes:
            return atribuicoes
        if not any(a.rota == "foto-hero" for a in atribuicoes) and self.temas_disponiveis:
            alvo = 1 if len(atribuicoes) > 1 else 0
            atribuicoes[alvo].rota = "foto-hero"
            atribuicoes[alvo].tema = self.temas_disponiveis[0]
        if len({a.rota for a in atribuicoes}) < 2 and len(atribuicoes) >= 2:
            alt = next((r for r in _ROTAS if r != atribuicoes[-1].rota), "tipografico")
            atribuicoes[-1].rota = alt
            atribuicoes[-1].tema = (
                self.temas_disponiveis[0] if alt == "foto-hero" and self.temas_disponiveis else None
            )
        return atribuicoes

    def _prompt(self, pautas: list[Pauta], knowledge: dict[str, Any], digest: str) -> str:
        linhas = "\n".join(
            f"  {i + 1}. pilar {pauta.pilar} - {pauta.titulo}" for i, pauta in enumerate(pautas)
        )
        return (
            "Voce e o Diretor Criativo. Atribua a CADA pauta do lote uma rota, tema e gancho, "
            "MAXIMIZANDO variedade (nao repita a mesma rota; espalhe temas; "
            "case conteudo<->formato).\n\n"
            f"BRIEFING:\n{knowledge.get('briefing', '')}\n\nTENDENCIAS:\n{digest}\n\n"
            f"PAUTAS:\n{linhas}\n\n"
            f"ROTAS: {list(_ROTAS)}\nTEMAS (p/ foto-hero): {self.temas_disponiveis}\n\n"
            "REGRA: pelo menos 2 rotas distintas no lote e pelo menos 1 foto-hero.\n\n"
            "Devolva APENAS YAML:\n"
            "atribuicoes:\n  - rota: <rota>\n    tema: <tema ou vazio>\n    "
            "gancho_padrao_id: <id>\n"
            "  (uma entrada por pauta, na ordem)\n"
        )
