import sys
from datetime import datetime

import typer

from stella.app import Stella, build_stella
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


def main() -> None:
    """Entry point declarado em pyproject.toml."""
    app()


if __name__ == "__main__":
    main()
