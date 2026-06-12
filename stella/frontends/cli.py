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
app.add_typer(agent_app, name="agent")


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


def main() -> None:
    """Entry point declarado em pyproject.toml."""
    app()


if __name__ == "__main__":
    main()
