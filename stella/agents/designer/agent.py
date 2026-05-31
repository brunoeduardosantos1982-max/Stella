"""Designer: gera DesignSpec JSON com decisoes de template/foto por slide."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

import yaml

from stella.agents.agente_marca_mktmagneto.planejador import _strip_code_fence
from stella.agents.designer.creative_index import (
    ReferenceBrief,
    brief_para_prompt,
    carregar_index,
    filtrar,
)
from stella.agents.designer.spec import DesignSpec, SlideSpec
from stella.agents.designer.temas.registry import TEMAS
from stella.framework.agent import Agent as BaseAgent
from stella.framework.agent import AgentOutput

_BRT = timezone(timedelta(hours=-3))
_PENDENTES_DIR = "C04 Claude Obsidian/Stella-publicacao/pendentes"
_FOTOS_FOLDER = "A03 Banco de Imagens/FotosBruno"
_FOTO_EXTS: set[str] = {".jpg", ".jpeg", ".png", ".webp"}
_TEMPLATES_COM_FOTO: frozenset[str] = frozenset(
    {"capa-foto-bg", "capa-foto-split", "capa-foto-topo"}
)
_DIMS: dict[str, list[int]] = {
    "post-unico": [1080, 1350],
    "carrossel": [1080, 1350],
    "stories": [1080, 1920],
}
_FORMATOS_VIDEO: frozenset[str] = frozenset({"video", "reels"})


class Agent(BaseAgent):
    """Especialista de design: produz DesignSpec JSON, sem renderizar PNG."""

    def execute(self, input: dict[str, Any]) -> AgentOutput:  # noqa: A002
        if self._vault is None:
            return AgentOutput(resultado={}, sucesso=False, mensagens=["Vault nao injetado"])
        if self._llm is None:
            return AgentOutput(resultado={}, sucesso=False, mensagens=["LLM nao injetado"])

        pauta = input.get("pauta") or {}
        tipo = str(pauta.get("tipo", "carrossel"))

        if tipo in _FORMATOS_VIDEO:
            return self._spec_video(pauta)

        if tipo == "landing-page":
            return self._spec_landing_page(input)

        return self._spec_imagem(input, tipo)

    def _spec_video(self, pauta: dict[str, Any]) -> AgentOutput:
        spec = DesignSpec(formato="video", dimensoes=[], video_clarificacao="aguardando_input")
        path = self._salvar_spec(spec, pauta.get("titulo", "video"))
        return AgentOutput(resultado={"design_spec_path": path, "formato": "video"}, sucesso=True)

    def _spec_landing_page(self, input: dict[str, Any]) -> AgentOutput:
        pauta = input.get("pauta") or {}
        copy = input.get("copy") or {}
        knowledge_pack = input.get("knowledge_pack") or {}
        html = self._gerar_html_landing(knowledge_pack, pauta, copy)
        spec = DesignSpec(formato="landing-page", dimensoes=[], landing_page_html=html)
        path = self._salvar_spec(spec, pauta.get("titulo", "landing"))
        return AgentOutput(
            resultado={"design_spec_path": path, "formato": "landing-page"}, sucesso=True
        )

    def _spec_imagem(self, input: dict[str, Any], tipo: str) -> AgentOutput:
        pauta = input.get("pauta") or {}
        copy = input.get("copy") or {}
        knowledge_pack = input.get("knowledge_pack") or {}
        variedade_contexto = input.get("variedade_contexto") or []

        fotos = self._listar_recursos(_FOTOS_FOLDER)
        index = carregar_index(self._vault)
        brief = filtrar(index, pauta, copy)
        decisao = self._decidir_template(
            knowledge_pack, pauta, copy, fotos, brief, variedade_contexto
        )
        slides = self._construir_slides(pauta, copy, decisao, tipo)
        dimensoes = _DIMS.get(tipo, [1080, 1350])
        spec = DesignSpec(formato=tipo, dimensoes=dimensoes, slides=slides)  # type: ignore[arg-type]
        path = self._salvar_spec(spec, pauta.get("titulo", tipo))

        return AgentOutput(
            resultado={
                "design_spec_path": path,
                "formato": tipo,
                "slides_planejados": len(slides),
                "template_capa": slides[0].template if slides else "",
                "rota": decisao.get("rota", "tipografico"),
            },
            sucesso=True,
        )

    def _listar_recursos(self, folder: str) -> list[str]:
        try:
            caminhos = self._vault.list_files_in_folder(folder, _FOTO_EXTS)  # type: ignore[union-attr]
            return [p.rsplit("/", 1)[-1] for p in caminhos]
        except OSError:
            return []

    def _decidir_template(
        self,
        knowledge_pack: dict[str, Any],
        pauta: dict[str, Any],
        copy: dict[str, Any],
        fotos: list[str],
        brief: ReferenceBrief | None = None,
        variedade_contexto: list[str] | None = None,
    ) -> dict[str, Any]:
        paleta = knowledge_pack.get("paleta") or knowledge_pack.get("kit", "")
        tipo = pauta.get("tipo", "carrossel")
        titulo = pauta.get("titulo", "")
        legenda_preview = str(copy.get("legenda", ""))[:120]

        templates = ["capa-carrossel (sem foto - conteudo conceitual/abstrato)"]
        if fotos:
            templates += [
                "capa-foto-bg (foto de Bruno como fundo desfocado - historias pessoais)",
                "capa-foto-split (foto a direita, texto a esquerda - credibilidade)",
                "capa-foto-topo (foto no topo, headline embaixo - depoimentos/resultados)",
            ]

        fotos_txt = "\n".join(f"  - {f}" for f in fotos) if fotos else "  (nenhuma disponivel)"
        brief_txt = brief_para_prompt(brief) if brief is not None else ""
        vc = variedade_contexto or []
        var_txt = ", ".join(vc) or "nenhum"
        forcar_troca = len(vc) >= 2 and vc[-1] == vc[-2] and bool(fotos)
        diretiva_var = (
            f"Os ultimos 2 posts usaram '{vc[-1]}'. AGORA escolha um estilo DIFERENTE: "
            "se houver uma FotoBruno adequada no brief, use 'foto-local'. "
            "Nao repita o mesmo estilo 3x seguidas.\n\n"
            if forcar_troca
            else "Prefira VARIAR (nao repita o mesmo estilo).\n\n"
        )

        prompt = (
            "Voce e o Designer do Time de Marketing.\n"
            "Aplique `selecao-template-por-conteudo` e `composicao-visual-social-2026`.\n\n"
            f"PALETA: {paleta}\nFORMATO: {tipo}\nTITULO: {titulo}\nLEGENDA: {legenda_preview}\n\n"
            "TEMPLATES DISPONIVEIS:\n" + "\n".join(f"  - {t}" for t in templates) + "\n\n"
            f"FOTOS DO BRUNO:\n{fotos_txt}\n\n"
            f"{brief_txt}\n\n"
            f"ESTILOS JA USADOS NESTA LEVA: {var_txt}. "
            + diretiva_var
            + "Escolha a ROTA: 'tipografico' (Paper puro), "
            "'foto-local' (usar uma FotoBruno do brief), "
            "'foto-higgsfield' (gerar imagem com Soul ID quando houver soul_id_prompt), "
            "'foto-hero' (capa foto-heroi composta: Higgsfield + tipografia).\n"
            "Use foto para historias pessoais/credibilidade/resultados; "
            "tipografico para conceitual.\n\n"
            "'foto-hero' = capa foto-heroi composta (Higgsfield + tipografia). "
            "Se escolher foto-hero, informe tema (um de: mitos) e o bloco foto_hero.\n\n"
            "Devolva APENAS YAML:\n"
            "rota: <tipografico|foto-local|foto-higgsfield|foto-hero>\n"
            "tema: <mitos|vazio>\n"
            "template_escolhido: <nome-exato>\n"
            "foto_escolhida: <nome-do-arquivo-ou-vazio>\n"
            "soul_id_prompt: <prompt-para-Higgsfield-ou-null>\n"
            "referencias_usadas: [<arquivos-de-referencia-que-inspiraram-ou-vazio>]\n"
            "foto_hero: {headline, label_topo, sublabel, anotacoes:[ate2], "
            "logos:[claude/openai]} (ou vazio)\n"
            "rationale: <motivo>\n"
        )

        resposta = self._llm.select(complexity="high").complete(prompt).texto  # type: ignore[union-attr]
        try:
            dados = yaml.safe_load(_strip_code_fence(resposta)) or {}
        except yaml.YAMLError:
            dados = {}
        if not isinstance(dados, dict):
            dados = {}

        template = str(dados.get("template_escolhido", "capa-carrossel")).strip()
        if not template or template == "None":
            template = "capa-carrossel"
        foto = str(dados.get("foto_escolhida", "")).strip()
        if foto not in fotos:
            foto = ""
        rota = str(dados.get("rota", "tipografico")).strip() or "tipografico"
        soul_id_prompt = str(dados.get("soul_id_prompt") or "").strip() or None
        if rota not in {"tipografico", "foto-local", "foto-higgsfield", "foto-hero"}:
            rota = "tipografico"
        if rota == "foto-higgsfield":
            foto = ""
            if soul_id_prompt is None:
                rota = "tipografico"
                template = "capa-carrossel"
        elif template in _TEMPLATES_COM_FOTO and not fotos:
            template = "capa-carrossel"
        refs = dados.get("referencias_usadas") or []
        refs = [str(r) for r in refs] if isinstance(refs, list) else []
        tema = str(dados.get("tema") or "").strip() or None
        foto_hero_raw = dados.get("foto_hero")
        foto_hero = foto_hero_raw if isinstance(foto_hero_raw, dict) else None
        if rota == "foto-hero" and (tema not in TEMAS or not foto_hero):
            rota = "tipografico"
            tema = None
            foto_hero = None
        if rota != "foto-hero":
            tema = None
            foto_hero = None

        return {
            "rota": rota,
            "template_escolhido": template,
            "foto_escolhida": foto,
            "rationale": str(dados.get("rationale", "")),
            "soul_id_prompt": soul_id_prompt,
            "referencias_usadas": refs,
            "tema": tema,
            "foto_hero": foto_hero,
        }

    def _construir_slides(
        self,
        pauta: dict[str, Any],
        copy: dict[str, Any],
        decisao: dict[str, Any],
        tipo: str,
    ) -> list[SlideSpec]:
        if decisao.get("rota") == "foto-hero":
            return [
                SlideSpec(
                    index=0,
                    template="foto-hero",
                    conteudo={},
                    tema=decisao.get("tema"),
                    foto_hero=decisao.get("foto_hero"),
                )
            ]

        titulo = pauta.get("titulo", "")
        pilar = str(pauta.get("pilar", ""))
        tag = f"{pilar} - mktmagneto.ia" if pilar else "mktmagneto.ia"
        linha1, destaque = _split_headline(titulo)
        textos = copy.get("slides", [])
        total_conteudo = max(1, len(textos) - 1)

        capa = SlideSpec(
            index=0,
            template=decisao["template_escolhido"],
            conteudo={
                "headline_linha1": linha1,
                "headline_destaque": destaque,
                "tag": tag,
                "code_pauta": str(titulo).lower(),
                "code_formato": tipo,
            },
            foto=decisao["foto_escolhida"] or None,
            soul_id_prompt=decisao.get("soul_id_prompt"),
            referencias_usadas=decisao.get("referencias_usadas", []),
        )
        slides = [capa]

        if tipo == "carrossel":
            for i, texto in enumerate(textos[1:], start=1):
                slides.append(
                    SlideSpec(
                        index=i,
                        template="slide-conteudo",
                        conteudo={
                            "counter": f"{i + 1:02d} / {total_conteudo + 1:02d}",
                            "texto": _limpar_texto_slide(str(texto)),
                            "tag": tag,
                        },
                    )
                )

        return slides

    def _gerar_html_landing(
        self,
        knowledge_pack: dict[str, Any],
        pauta: dict[str, Any],
        copy: dict[str, Any],
    ) -> str:
        prompt = (
            "Gere uma landing page HTML completa e responsiva.\n"
            f"MARCA: {knowledge_pack.get('briefing', '')}\n"
            f"PALETA: {knowledge_pack.get('paleta', '')}\n"
            f"TITULO: {pauta.get('titulo', '')}\n"
            f"COPY: {copy.get('legenda', '')}\n\n"
            "Devolva APENAS o HTML completo (<!DOCTYPE html> ate </html>)."
        )
        return self._llm.select(complexity="high").complete(prompt).texto  # type: ignore[union-attr]

    def _salvar_spec(self, spec: DesignSpec, titulo: str) -> str:
        agora = datetime.now(_BRT).strftime("%Y%m%d-%H%M%S")
        slug = titulo[:20].replace(" ", "-").lower()
        path = f"{_PENDENTES_DIR}/{agora}-{slug}-spec.json"
        self._vault.write_binary(path, spec.to_json().encode("utf-8"))  # type: ignore[union-attr]
        return path


def _split_headline(titulo: str) -> tuple[str, str]:
    words = titulo.split()
    if not words:
        return "", ""
    if len(words) <= 3:
        return " ".join(words[:-1]), words[-1]
    cut = max(1, round(len(words) * 0.55))
    return " ".join(words[:cut]), " ".join(words[cut:])


def _limpar_texto_slide(texto: str) -> str:
    linhas = texto.replace("\r\n", "\n").split("\n")
    if linhas and re.match(r"^\s*SLIDE\s+\d+\b", linhas[0], flags=re.IGNORECASE):
        linhas = linhas[1:]
    if linhas and re.match(r'^\s*T[ií]tulo:\s*".*"\s*$', linhas[0], flags=re.IGNORECASE):
        linhas = linhas[1:]
    if linhas and re.match(r"^\s*Corpo:\s*$", linhas[0], flags=re.IGNORECASE):
        linhas = linhas[1:]
    return "\n".join(linhas).strip()
