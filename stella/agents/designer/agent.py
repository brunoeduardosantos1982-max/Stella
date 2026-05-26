"""Designer — DesignSpecGenerator: decide template/foto/conteúdo e salva design_spec.json."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import yaml

from stella.agents.agente_marca_mktmagneto.planejador import _strip_code_fence
from stella.agents.designer.spec import DesignSpec, SlideSpec
from stella.framework.agent import Agent as BaseAgent
from stella.framework.agent import AgentOutput

_BRT = timezone(timedelta(hours=-3))
_PENDENTES_DIR = "C04 Claude Obsidian/Stella-publicacao/pendentes"
_REFS_FOLDER = "A03 Banco de Imagens/referencias para criativos"
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
    """Especialista de design: produz DesignSpec JSON — não renderiza PNG."""

    def execute(self, input: dict[str, Any]) -> AgentOutput:  # noqa: A002
        if self._vault is None:
            return AgentOutput(resultado={}, sucesso=False, mensagens=["Vault não injetado"])
        if self._llm is None:
            return AgentOutput(resultado={}, sucesso=False, mensagens=["LLM não injetado"])

        pauta = input.get("pauta") or {}
        tipo = str(pauta.get("tipo", "carrossel"))

        if tipo in _FORMATOS_VIDEO:
            return self._spec_video(pauta)

        if tipo == "landing-page":
            return self._spec_landing_page(input)

        return self._spec_imagem(input, tipo)

    # ── formatos ────────────────────────────────────────────────────────────────

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

        fotos = self._listar_recursos(_FOTOS_FOLDER)
        decisao = self._decidir_template(knowledge_pack, pauta, copy, fotos)
        slides = self._construir_slides(pauta, copy, decisao, fotos, tipo)
        dimensoes = _DIMS.get(tipo, [1080, 1350])
        spec = DesignSpec(formato=tipo, dimensoes=dimensoes, slides=slides)  # type: ignore[arg-type]
        path = self._salvar_spec(spec, pauta.get("titulo", tipo))

        return AgentOutput(
            resultado={
                "design_spec_path": path,
                "formato": tipo,
                "slides_planejados": len(slides),
                "template_capa": slides[0].template if slides else "",
            },
            sucesso=True,
        )

    # ── helpers ─────────────────────────────────────────────────────────────────

    def _listar_recursos(self, folder: str) -> list[str]:
        try:
            caminhos = self._vault.list_files_in_folder(folder, _FOTO_EXTS)  # type: ignore[union-attr]
            return [p.rsplit("/", 1)[-1] for p in caminhos]
        except (FileNotFoundError, PermissionError):
            return []

    def _decidir_template(
        self,
        knowledge_pack: dict[str, Any],
        pauta: dict[str, Any],
        copy: dict[str, Any],
        fotos: list[str],
    ) -> dict[str, Any]:
        paleta = knowledge_pack.get("paleta") or knowledge_pack.get("kit", "")
        tipo = pauta.get("tipo", "carrossel")
        titulo = pauta.get("titulo", "")
        legenda_preview = str(copy.get("legenda", ""))[:120]

        templates = ["capa-carrossel (sem foto — ideal para conteúdo conceitual/abstrato)"]
        if fotos:
            templates += [
                "capa-foto-bg (foto de Bruno como fundo desfocado — histórias pessoais)",
                "capa-foto-split (foto à direita, texto à esquerda — credibilidade)",
                "capa-foto-topo (foto no topo, headline embaixo — depoimentos/resultados)",
            ]

        fotos_txt = "\n".join(f"  - {f}" for f in fotos) if fotos else "  (nenhuma disponível)"

        prompt = (
            "Você é o Designer do Time de Marketing.\n"
            "Aplique as skills `selecao-template-por-conteudo` e `composicao-visual-social-2026`.\n\n"
            f"PALETA: {paleta}\nFORMATO: {tipo}\nTÍTULO: {titulo}\nLEGENDA: {legenda_preview}\n\n"
            "TEMPLATES DISPONÍVEIS:\n" + "\n".join(f"  - {t}" for t in templates) + "\n\n"
            f"FOTOS DO BRUNO:\n{fotos_txt}\n\n"
            "Prefira templates com foto para posts de história pessoal, credibilidade ou resultados.\n"
            "Use capa-carrossel para conteúdo conceitual/técnico.\n\n"
            "Devolva APENAS YAML:\n"
            "template_escolhido: <nome-exato>\n"
            "foto_escolhida: <nome-do-arquivo-ou-vazio>\n"
            "rationale: <motivo>\n"
            "soul_id_prompt: <prompt-higgsfield-ou-null>\n"
        )

        resposta = self._llm.select(complexity="low").complete(prompt).texto  # type: ignore[union-attr]
        try:
            dados = yaml.safe_load(_strip_code_fence(resposta)) or {}
        except yaml.YAMLError:
            dados = {}
        if not isinstance(dados, dict):
            dados = {}

        template = str(dados.get("template_escolhido", "capa-carrossel")).strip()
        foto = str(dados.get("foto_escolhida", "")).strip()
        if template in _TEMPLATES_COM_FOTO and not fotos:
            template = "capa-carrossel"
        if foto not in fotos:
            foto = ""

        return {
            "template_escolhido": template,
            "foto_escolhida": foto,
            "rationale": str(dados.get("rationale", "")),
            "soul_id_prompt": dados.get("soul_id_prompt") or None,
        }

    def _construir_slides(
        self,
        pauta: dict[str, Any],
        copy: dict[str, Any],
        decisao: dict[str, Any],
        fotos: list[str],
        tipo: str,
    ) -> list[SlideSpec]:
        titulo = pauta.get("titulo", "")
        pilar = str(pauta.get("pilar", ""))
        tag = f"{pilar} · mktmagneto.ia" if pilar else "mktmagneto.ia"
        linha1, destaque = _split_headline(titulo)

        capa = SlideSpec(
            index=0,
            template=decisao["template_escolhido"],
            conteudo={"headline_linha1": linha1, "headline_destaque": destaque, "tag": tag},
            foto=decisao["foto_escolhida"] or None,
            soul_id_prompt=decisao.get("soul_id_prompt"),
        )
        slides = [capa]

        if tipo == "carrossel":
            textos = copy.get("slides", [])
            for i, texto in enumerate(textos[1:], start=1):
                slides.append(
                    SlideSpec(
                        index=i,
                        template="slide-conteudo",
                        conteudo={"texto": str(texto), "tag": tag},
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
            f"TÍTULO: {pauta.get('titulo', '')}\n"
            f"COPY: {copy.get('legenda', '')}\n\n"
            "Devolva APENAS o HTML completo (<!DOCTYPE html> até </html>)."
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
