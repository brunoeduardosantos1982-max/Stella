import sys
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import cast

import typer

from stella.adapters.higgsfield.base import HiggsFieldClient, HiggsFieldError
from stella.adapters.higgsfield.client import CliHiggsFieldClient
from stella.adapters.higgsfield.resolvedor import ResolvedorImagens, _baixar_http
from stella.adapters.vault.base import VaultRepository
from stella.agents.designer.spec import DesignSpec
from stella.app import Stella, build_stella
from stella.corpo.daemon_telegram import run_daemon
from stella.corpo.ear_prompter import gerar as gerar_ear_prompter
from stella.corpo.gravador import (
    COFRE_TELEGRAM,
    PASTA_GRAVACOES,
    VAULT_DIR,
    processar_pasta,
    vigiar_pasta,
)
from stella.framework.cli.agent_cli import agent_app
from stella.framework.errors import (
    AgentExecutionError,
    AgentInputError,
    AgentNotFoundError,
    AgentTimeoutError,
    AgentUnavailableError,
    BudgetExceededError,
    DelegationDepthExceeded,
    FrameworkError,
    ManifestError,
    MCPError,
    QualityReviewFailed,
    SkillNotFoundError,
)
from stella.infra.config import StellaConfig
from stella.usecases.atualizar_memoria import RegistroInteracao
from stella.usecases.base import UsecaseError
from stella.usecases.capturar_ideia import EntradaCaptura
from stella.usecases.responder_projeto import EntradaPergunta


def _traduzir_erro_jarvis(erro: FrameworkError) -> str:
    """Traduz qualquer FrameworkError numa mensagem em tom Jarvis para o Bruno.

    Mapeia cada subclasse conhecida para uma frase especifica. Subclasse
    desconhecida cai no fallback generico.
    """
    msg = str(erro)
    if isinstance(erro, AgentNotFoundError):
        return f"Senhor, agente solicitado nao foi encontrado: {msg}"
    if isinstance(erro, AgentUnavailableError):
        return f"Senhor, o agente esta offline: {msg}. Deseja iniciar o servidor?"
    if isinstance(erro, AgentTimeoutError):
        return f"Senhor, o agente demorou demais para responder: {msg}. Cancelei."
    if isinstance(erro, AgentExecutionError):
        return f"Senhor, o agente falhou ao executar: {msg}"
    if isinstance(erro, AgentInputError):
        return f"Senhor, o pedido enviado ao agente esta incompleto: {msg}"
    if isinstance(erro, ManifestError):
        return f"Senhor, configuracao do manifest invalida: {msg}"
    if isinstance(erro, DelegationDepthExceeded):
        return f"Senhor, detectei um loop de delegacao (profundidade excedida): {msg}"
    if isinstance(erro, BudgetExceededError):
        return f"Senhor, atingimos o teto de orcamento: {msg}. Pausei novas chamadas LLM."
    if isinstance(erro, QualityReviewFailed):
        return f"Senhor, a revisao de qualidade reprovou o output: {msg}"
    if isinstance(erro, SkillNotFoundError):
        return f"Senhor, skill solicitada nao esta registrada: {msg}"
    if isinstance(erro, MCPError):
        return f"Senhor, integracao MCP falhou: {msg}"
    return f"Senhor, ocorreu um erro do framework: {msg}"


def _forcar_stdout_utf8() -> None:
    """No Windows, o console default usa cp1252 e estoura em emojis (✅, ⚠️, etc).

    Sonnet costuma devolver respostas com emojis — sem este reconfigure, qualquer
    `typer.echo` com emoji levanta UnicodeEncodeError. Idempotente.
    """
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


_forcar_stdout_utf8()

app = typer.Typer(help="Stella — assistente pessoal do Bruno.")
lembrete_app = typer.Typer(help="Lembretes temporizados da Stella.")
app.add_typer(agent_app, name="agent")
app.add_typer(lembrete_app, name="lembrete")

_EAR_PROMPTER_SAIDA_PADRAO = Path("tmp/.secrets/ear-prompter.mp3")


def _build_stella_para_cli() -> Stella:
    cfg = StellaConfig()
    return build_stella(cfg)


def _build_higgsfield_client(aspect_ratio: str = "1:1", quality: str = "2k") -> HiggsFieldClient:
    # A autenticação é do próprio `hf` (token salvo via `hf auth login`); não passamos token.
    return CliHiggsFieldClient(aspect_ratio=aspect_ratio, quality=quality)


@app.command()
def anota(texto: str = typer.Argument(..., help="Texto livre da ideia")) -> None:
    """Captura uma ideia rápida no vault (A00 Inbox)."""
    stella = _build_stella_para_cli()
    momento = datetime.now()
    try:
        resultado = stella.capturar_ideia.execute(EntradaCaptura(texto=texto, momento=momento))
        typer.echo(f"Anotado em [[{resultado.path}]] — {resultado.titulo}")
        stella.atualizar_memoria.execute(
            RegistroInteracao(
                momento=momento,
                usecase="capturar_ideia",
                input_usuario=f'anota "{texto}"',
                resposta_stella=f"Anotado em {resultado.path}",
            )
        )
    except UsecaseError as e:
        typer.echo(f"Senhor, não consegui anotar: {e}", err=True)
        raise typer.Exit(code=1) from e


@app.command()
def pergunta(
    projeto: str = typer.Argument(..., help="Nome do projeto em B01 Projetos"),
    pergunta: str = typer.Argument(..., help="Pergunta a responder"),
) -> None:
    """Responde uma pergunta sobre um projeto do vault."""
    stella = _build_stella_para_cli()
    momento = datetime.now()
    try:
        resultado = stella.responder_projeto.execute(
            EntradaPergunta(pergunta=pergunta, projeto=projeto)
        )
        typer.echo(resultado.resposta)
        stella.atualizar_memoria.execute(
            RegistroInteracao(
                momento=momento,
                usecase="responder_projeto",
                input_usuario=f'pergunta "{projeto}": {pergunta}',
                resposta_stella=resultado.resposta,
            )
        )
    except UsecaseError as e:
        typer.echo(f"Senhor, não consegui responder: {e}", err=True)
        raise typer.Exit(code=1) from e


@app.command()
def conteudo(
    marca: str = typer.Argument(..., help="Marca alvo (ex: mktmagneto)"),
) -> None:
    """Gera o lote semanal de conteúdo da marca (rascunhos na fila do publicador)."""
    if marca != "mktmagneto":
        typer.echo(f"Senhor, ainda só conheço o agente da marca 'mktmagneto'. Recebi '{marca}'.")
        raise typer.Exit(code=2)

    stella = _build_stella_para_cli()
    agente = stella.registry.get("agente_marca_mktmagneto")
    out = agente.execute({})

    if out.sucesso:
        n = out.resultado.get("posts_em_rascunho", 0)
        msg = " ".join(out.mensagens) if out.mensagens else ""
        typer.echo(f"Senhor, {n} post(s) em rascunho na fila. {msg}".strip())
    else:
        typer.echo(f"Senhor, deu ruim: {' / '.join(out.mensagens)}")
        raise typer.Exit(code=1)


@app.command()
def publicar() -> None:
    """Publica os posts da fila (C04 Claude Obsidian/Stella-publicacao/fila/)."""
    cfg = StellaConfig()
    stella = _build_stella_para_cli()
    try:
        cliente = stella.registry.get("agente_publicador")
        saida = cliente.execute(
            {
                "modo": cfg.publicacao_modo,
                "postiz_token": cfg.postiz_token.get_secret_value(),
            }
        )
    except FrameworkError as e:
        typer.echo(_traduzir_erro_jarvis(e), err=True)
        raise typer.Exit(code=1) from e

    for linha in saida.mensagens:
        typer.echo(linha)
    if not saida.sucesso:
        raise typer.Exit(code=1)


@app.command("gerar-imagem")
def gerar_imagem(
    prompt: str = typer.Argument(..., help="Prompt visual para o Higgsfield"),
    aspect_ratio: str = typer.Option(
        "1:1", "--aspect-ratio", help="1:1, 16:9, 9:16, 4:3, 3:4, 3:2, 2:3"
    ),
    soul_id: str | None = typer.Option(
        None, "--soul-id", help="(ainda não suportado — treine via hf soul-id)"
    ),
) -> None:
    """Gera uma imagem via Higgsfield (modelo Soul V2) e imprime a URL retornada."""
    soul = soul_id or (StellaConfig().higgsfield_soul_id or None)
    try:
        cliente = _build_higgsfield_client(aspect_ratio=aspect_ratio)
        url = cliente.generate_image(prompt, soul_id=soul)
    except (HiggsFieldError, RuntimeError) as e:
        typer.echo(f"Senhor, nao consegui gerar imagem no Higgsfield: {e}", err=True)
        raise typer.Exit(code=1) from e
    typer.echo(url)


_FILA_DIR = "C04 Claude Obsidian/Stella-publicacao/fila"


def _fab_dir() -> Path:
    """Pasta da fábrica de conteúdo v2 no vault."""
    return StellaConfig().vault_path / "C04 Claude Obsidian/outputs/FABRICADECONTEUDO"


def _registro_path() -> Path:
    """JSON do registro de keywords (fonte da verdade da fábrica)."""
    return _fab_dir() / "registro-keywords.json"


def resolver_imagens_para_fila(
    *,
    vault: VaultRepository,
    higgs: HiggsFieldClient,
    baixar: Callable[[str], bytes] = _baixar_http,
    post_id: str | None,
) -> list[str]:
    """Re-resolve slides foto-higgsfield pendentes na fila. Retorna mensagens."""
    msgs: list[str] = []
    for nota_path in vault.list_notes_in_folder(_FILA_DIR):
        nome = nota_path.rsplit("/", 1)[-1].removesuffix(".md")
        if post_id is not None and nome != post_id:
            continue
        nota = vault.read_note(nota_path)
        if nota.frontmatter.get("status") != "needs_review":
            continue
        spec_path = str(nota.frontmatter.get("design_spec", ""))
        if not spec_path:
            continue
        spec = DesignSpec.from_json(vault.read_binary(spec_path).decode("utf-8"))
        warnings = ResolvedorImagens(higgs=higgs, vault=vault, baixar=baixar).resolver(
            spec, post_id=nome
        )
        vault.write_binary(spec_path, spec.to_json().encode("utf-8"))
        imagens = [s.foto for s in spec.slides if s.foto]
        novo_status = "needs_review" if warnings else "pending_render"
        vault.update_frontmatter(nota_path, {"status": novo_status, "imagens": imagens})
        msgs.append(f"{nome}: {novo_status} ({len(imagens)} imagem(ns))")
    return msgs


@app.command("resolver-imagens")
def resolver_imagens(
    post_id: str | None = typer.Argument(None, help="post_id específico, ou todos needs_review"),
) -> None:
    """Re-tenta gerar as imagens Higgsfield dos posts needs_review na fila."""
    stella = _build_stella_para_cli()
    higgs = next(iter(stella.mcp_reg.list_by_category("image")), None)
    if higgs is None:
        typer.echo("Senhor, nenhum MCP de imagem registrado (higgsfield).", err=True)
        raise typer.Exit(code=1)
    msgs = resolver_imagens_para_fila(
        vault=stella.vault, higgs=cast(HiggsFieldClient, higgs), post_id=post_id
    )
    if not msgs:
        typer.echo("Nada a resolver (nenhum post needs_review).")
        return
    for m in msgs:
        typer.echo(m)


@app.command()
def gravador(
    watch: bool = typer.Option(False, "--watch", help="Vigia a pasta de gravacoes em loop"),
    pasta: Path | None = typer.Option(None, "--pasta", help="Pasta com audios e videos"),  # noqa: B008
    vault_dir: Path | None = typer.Option(None, "--vault-dir", help="Raiz do vault Obsidian"),  # noqa: B008
    cofre_path: Path | None = typer.Option(None, "--cofre-path", help="Cofre Telegram"),  # noqa: B008
) -> None:
    """Transcreve gravacoes, salva no vault e avisa o Telegram."""
    pasta = pasta or PASTA_GRAVACOES
    vault_dir = vault_dir or VAULT_DIR
    cofre_path = cofre_path or COFRE_TELEGRAM
    stella = _build_stella_para_cli()
    if watch:
        typer.echo("Senhor, gravador em vigia. Vou observar a pasta de reuniões.")
        vigiar_pasta(pasta, vault_dir, cofre_path, stella.anthropic)
        return

    total = processar_pasta(pasta, vault_dir, cofre_path, stella.anthropic)
    if total == 0:
        typer.echo("Senhor, pasta vazia ou sem gravações novas.")
        return
    typer.echo(f"Senhor, processei {total} gravação(ões) e deixei tudo registrado.")


_BANNER_DAEMON = """
  ███████╗████████╗███████╗██╗     ██╗      █████╗
  ██╔════╝╚══██╔══╝██╔════╝██║     ██║     ██╔══██╗
  ███████╗   ██║   █████╗  ██║     ██║     ███████║
  ╚════██║   ██║   ██╔══╝  ██║     ██║     ██╔══██║
  ███████║   ██║   ███████╗███████╗███████╗██║  ██║
  ╚══════╝   ╚═╝   ╚══════╝╚══════╝╚══════╝╚═╝  ╚═╝
"""


@app.command()
def seguranca() -> None:
    """Roda a verificação de segurança diária do vault (determinística, sem LLM)."""
    from stella.corpo.seguranca import montar_card, rodar_seguranca_diaria

    relatorio = rodar_seguranca_diaria()
    typer.echo(montar_card(relatorio))
    if relatorio.criticos:
        raise typer.Exit(code=1)


@app.command()
def radar(
    n: int = typer.Option(5, "--n", help="Quantos artigos neste drop (6h=5, 14h=3, 19h=3)."),
) -> None:
    """Busca notícias quentes dos nichos do Bruno e manda o card no Telegram."""
    from stella.corpo.radar import label_horario, montar_card, rodar_radar

    try:
        itens = rodar_radar(n=n)
    except Exception as e:
        typer.echo(f"Senhor, o radar falhou: {e}", err=True)
        raise typer.Exit(code=1) from e
    typer.echo(montar_card(itens, label_horario()))


@app.command()
def notificar(texto: str = typer.Argument(..., help="Texto para enviar agora no Telegram")) -> None:
    """Envia uma notificação imediata no Telegram."""
    from stella.corpo.lembretes import notificar as notificar_telegram

    try:
        notificar_telegram(texto)
    except Exception as e:
        typer.echo(f"Senhor, nao consegui notificar no Telegram: {e}", err=True)
        raise typer.Exit(code=1) from e
    typer.echo("Notificacao enviada.")


@app.command("ear-prompter")
def ear_prompter(
    texto: str = typer.Argument(..., help="Roteiro a transformar em audio pausado"),
    gap: float = typer.Option(5.0, "--gap", "-g", help="Silencio entre frases, em segundos"),
    saida: Path | None = typer.Option(  # noqa: B008
        None, "--saida", "-s", help="Arquivo MP3 de saida"
    ),
) -> None:
    """Gera MP3 de teleprompter auditivo com pausas entre frases."""
    destino = saida or _EAR_PROMPTER_SAIDA_PADRAO
    try:
        gerado = gerar_ear_prompter(texto, destino, gap_seg=gap)
    except ValueError as e:
        typer.echo(f"Senhor, roteiro invalido: {e}", err=True)
        raise typer.Exit(code=2) from e
    except Exception as e:
        typer.echo(f"Senhor, nao consegui gerar o ear-prompter: {e}", err=True)
        raise typer.Exit(code=1) from e
    typer.echo(str(gerado))


@app.command("enviar-audio")
def enviar_audio(
    caminho: str = typer.Argument(..., help="Caminho do MP3 para enviar no Telegram"),
) -> None:
    """Envia um arquivo de audio (ex.: ear-prompter) ao chat do Bruno no Telegram."""
    from stella.corpo.daemon_telegram import load_secrets, send_voice

    secrets = load_secrets()
    send_voice(secrets.bot_token, secrets.chat_id, Path(caminho))
    typer.echo("Audio enviado.")


@lembrete_app.command("add")
def lembrete_add(
    quando: str = typer.Option(..., "--quando", "-q", help='ISO ou "HH:MM"'),
    texto: str = typer.Option(..., "--texto", "-t", help="Texto do lembrete"),
) -> None:
    """Cria um lembrete pendente."""
    from stella.corpo.lembretes import adicionar

    try:
        lembrete = adicionar(quando, texto)
    except ValueError as e:
        typer.echo(f"Senhor, horario invalido: {e}", err=True)
        raise typer.Exit(code=2) from e
    typer.echo(f"{lembrete['id']} | {lembrete['quando']} | {lembrete['texto']}")


@lembrete_app.command("list")
def lembrete_list() -> None:
    """Lista lembretes pendentes."""
    from stella.corpo.lembretes import listar

    itens = listar()
    if not itens:
        typer.echo("Nenhum lembrete pendente.")
        return
    for item in itens:
        typer.echo(f"{item['id']} | {item['quando']} | {item['texto']}")


@lembrete_app.command("remover")
def lembrete_remover(id: str = typer.Argument(..., help="ID do lembrete")) -> None:
    """Remove um lembrete pelo ID."""
    from stella.corpo.lembretes import remover

    if not remover(id):
        typer.echo(f"Lembrete nao encontrado: {id}", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"Lembrete removido: {id}")


@lembrete_app.command("tick")
def lembrete_tick() -> None:
    """Dispara lembretes vencidos. Comando barato para agendador."""
    from stella.corpo.lembretes import disparar_pendentes

    enviados = disparar_pendentes()
    typer.echo(f"Lembretes enviados: {len(enviados)}")


@app.command()
def daemon() -> None:
    """Inicia o daemon Telegram que conversa com Claude Code."""
    typer.echo(_BANNER_DAEMON)
    typer.echo("  🧠 Cérebro : Claude Code")
    typer.echo("  📡 Corpo   : daemon Telegram")
    typer.echo("  🎤 Voz     : ouve e fala (whisper + edge-tts)")
    typer.echo(f"  🕐 Início  : {datetime.now():%d/%m/%Y %H:%M:%S}")
    typer.echo("")
    typer.echo("  Senhor, estou de ouvidos abertos no Telegram.")
    typer.echo("")
    try:
        run_daemon()
    except KeyboardInterrupt:
        typer.echo("Senhor, daemon encerrado com segurança.")


@app.command()
def carrossel(
    json_path: str = typer.Argument(..., help="JSON do post (slides capa/conteudo/cta)"),
    outdir: str = typer.Argument(..., help="Pasta de saída dos slide-NN.png"),
    chrome: str | None = typer.Option(None, "--chrome", help="Caminho do Chrome/Edge"),
) -> None:
    """Renderiza os slides de um carrossel (Field Manual escuro) em PNG."""
    import json as _json

    from stella.adapters.render.carrossel import renderizar_post

    post = _json.loads(Path(json_path).read_text(encoding="utf-8"))
    try:
        feitos = renderizar_post(post, outdir, chrome=chrome)
    except (ValueError, RuntimeError) as e:
        typer.echo(f"Senhor, não consegui renderizar: {e}", err=True)
        raise typer.Exit(code=1) from e
    for caminho, ok in feitos:
        typer.echo(f"{caminho.name}: {'OK' if ok else 'FALHOU'}")


@app.command()
def material(
    keyword: str = typer.Argument(..., help="Keyword do ManyChat (ex.: ERROS)"),
    html: str = typer.Option(..., "--html", help="Arquivo HTML do material"),
    slug: str = typer.Option(..., "--slug", help="Slug do PDF (ex.: diagnostico-erros-ia)"),
    material_txt: str = typer.Option("", "--material", help="Conceito/título do material"),
    chrome: str | None = typer.Option(None, "--chrome", help="Caminho do Chrome/Edge"),
) -> None:
    """Renderiza o material HTML->PDF, valida layout/fontes e registra a keyword."""
    from stella.adapters.render.material import (
        contar_paginas_pdf,
        fontes_embutidas,
        renderizar_pdf,
        validar_layout,
    )
    from stella.domain.registro_keywords import RegistroKeywords, normalizar_keyword

    pdf_out = _fab_dir() / normalizar_keyword(keyword) / f"{slug}.pdf"
    html_str = Path(html).read_text(encoding="utf-8")
    try:
        pdf_bytes = renderizar_pdf(html, pdf_out, chrome=chrome)
        if not fontes_embutidas(pdf_bytes):
            raise ValueError("fontes não embutidas (a CSS compartilhada não carregou?)")
        paginas = contar_paginas_pdf(pdf_bytes)
        validar_layout(html_str, paginas)
    except (ValueError, RuntimeError) as e:
        typer.echo(f"Senhor, material reprovado: {e}", err=True)
        raise typer.Exit(code=2) from e
    reg_path = _registro_path()
    reg = RegistroKeywords.carregar(reg_path)
    reg.definir_material(keyword, slug=slug, material=material_txt)
    reg.salvar(reg_path)
    typer.echo(f"OK: {pdf_out} ({paginas} páginas)")


@app.command()
def manychat(
    keyword: str = typer.Argument(..., help="Keyword do ManyChat"),
) -> None:
    """Gera/atualiza a config do ManyChat da keyword a partir do registro."""
    from stella.corpo.manychat import escrever_manychat
    from stella.domain.registro_keywords import RegistroKeywords, normalizar_keyword

    reg = RegistroKeywords.carregar(_registro_path())
    entrada = reg.buscar(keyword)
    if entrada is None:
        typer.echo(f"Senhor, a keyword '{keyword}' não está no registro ainda.", err=True)
        raise typer.Exit(code=1)
    destino = _fab_dir() / normalizar_keyword(keyword)
    caminho = escrever_manychat(entrada, destino)
    typer.echo(str(caminho))


@app.command("publicar-material")
def publicar_material_cmd(
    slug: str = typer.Argument(..., help="Slug do material PDF a publicar"),
) -> None:
    """Hospeda o PDF do material no hub (commit + deploy). Gate 2: só após ok do Bruno."""
    from stella.corpo.publicar_material import HUB_REPO, deploy_hub, publicar_material

    try:
        url = publicar_material(
            slug,
            fab_dir=_fab_dir(),
            hub_materiais=HUB_REPO / "public" / "materiais",
            deploy_fn=deploy_hub,
        )
    except FileNotFoundError as e:
        typer.echo(f"Senhor, não achei o PDF do material: {e}", err=True)
        raise typer.Exit(code=1) from e
    except Exception as e:
        typer.echo(f"Senhor, o deploy falhou: {e}", err=True)
        raise typer.Exit(code=1) from e
    typer.echo(url)


@app.command()
def drop(
    referencia: str = typer.Argument(..., help="Apelido do drop do Radar (ex.: ia-google-agentes)"),
) -> None:
    """Resolve um apelido do Radar e imprime a noticia-fonte (para o modo carrossel)."""
    import json as _json

    from stella.corpo.radar_drops import DROPS_PATH, carregar_drops, resolver_drop

    achados = resolver_drop(referencia, carregar_drops(DROPS_PATH))
    if not achados:
        typer.echo(f"Senhor, nao achei nenhum drop para '{referencia}'.", err=True)
        raise typer.Exit(code=1)
    if len(achados) > 1:
        apelidos = ", ".join(a.get("apelido", "?") for a in achados)
        typer.echo(f"Ambiguo ({len(achados)} drops). Qual destes? {apelidos}")
        raise typer.Exit(code=2)
    typer.echo(_json.dumps(achados[0], ensure_ascii=False, indent=2))


def main() -> None:
    """Entry point declarado em pyproject.toml."""
    app()


if __name__ == "__main__":
    main()
