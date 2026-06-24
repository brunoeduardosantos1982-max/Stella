from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import httpx

from stella.corpo.persona_carrossel import GATILHO_CARROSSEL, PERSONA_CARROSSEL

COFRE_TELEGRAM = Path("D:/VortexBrain00/.secrets/telegram.json")
DAEMON_STATE = Path("D:/VortexBrain00/.secrets/daemon_state.json")
DAEMON_LOG = Path("D:/VortexBrain00/.secrets/daemon.log")
SESSION_STATE = Path("D:/VortexBrain00/.secrets/stella_sessao.json")
CONTEUDO_STATE = Path("D:/VortexBrain00/.secrets/stella_conteudo.json")
CONTEUDO_TTL_MIN = 30
CLAUDE_CWD = Path("D:/VortexBrain00")
TELEGRAM_CHUNK_MAX = 4000

# Modelo da Stella no Telegram: Sonnet por padrão (econômico p/ assistente).
# A frase-gatilho "Stella eu preciso do Opus" (em qualquer lugar da mensagem;
# o "Stella eu" é opcional) ativa o Opus só naquela tarefa.
MODELO_PADRAO = "claude-sonnet-4-6"
MODELO_OPUS = "claude-opus-4-8"
GATILHO_OPUS = re.compile(
    r"\b(stella[,]?\s+eu\s+)?preciso\s+do\s+opus\b[\s,.:;!-]*",
    re.IGNORECASE,
)

# Persona injetada no claude -p: faz a Stella INTERPRETAR e sugerir (nao ecoar texto cru),
# em texto plano conversacional (o Telegram nao renderiza markdown e a voz nao le simbolos).
PERSONA_STELLA = (
    "Você é a Stella, assistente pessoal do Bruno, respondendo pelo Telegram. "
    "NÃO repita nem leia o pedido de volta literalmente: interprete o que ele quis dizer, "
    "resuma e responda como uma estrategista afiada e calorosa — direta, natural e com "
    "SUGESTÕES concretas de próximo passo quando fizer sentido. "
    "Trate-o por 'Senhor' no começo do dia e 'Bruno' ao longo dele; tom Jarvis, humor seco sutil. "
    "Responda SEMPRE em texto plano conversacional: nada de markdown, asteriscos, '#', tabelas "
    "ou listas com símbolos (o Telegram mostra os símbolos crus e a voz não os lê). "
    "Escreva números, datas e horas de forma natural de fala "
    "(ex.: 'dia dezesseis de junho, às cinco da tarde', não '16/06 17:00'). "
    "Confirme em uma frase o que foi feito e ofereça o próximo passo. Seja concisa. "
    "Para lembretes futuros (ex.: 'me lembra às 16h de algo'), você TEM uma ferramenta de verdade: "
    "rode o comando uv run stella lembrete add -q HORARIO -t TEXTO (HORARIO em HH:MM ou ISO) e "
    "confirme que agendou. Você NÃO executa nada em segundo plano: o que dá pra fazer agora, faça "
    "e relate o resultado; nunca prometa 'te aviso quando terminar' sem ter criado um lembrete real."
)

# Modo conteúdo: detecta pedido de criação de conteúdo (roda em Opus).
GATILHO_CONTEUDO = re.compile(r"\b(script|roteiro|reels?|pauta|conte[úu]do)\b", re.IGNORECASE)
# Verbo de criação: distingue um PEDIDO NOVO ("cria um script sobre X") de um
# seguimento ("melhora", "o ear-prompter do script"). Pedido novo zera a sessão.
_RE_ACAO_NOVA = re.compile(
    r"\b(cri[ae]r?|crie|fa[çz]\w*|quero|ger[ae]r?|gere|mont[ae]r?|monte|novo|nova)\b",
    re.IGNORECASE,
)

PERSONA_CONTEUDO = (
    "MODO CONTEÚDO ATIVO — conteúdo para @brunoe.santos. Fluxo em 3 ETAPAS; uma etapa por vez, "
    "nunca pule. Do pedido extraia o TEMA (assunto principal) e o GANCHO (ângulo/atualidade). "
    "ETAPA 1 — OPÇÕES COM ROTEIROS: pesquise referência (skill notebooklm no notebook de nome igual "
    "ao TEMA: marketing, ia, viagem, tecnologia, vendas, gastronomia, personal brand; se não houver, "
    "web; o GANCHO sempre na web). Entregue 3 OPÇÕES, cada uma com a pauta E o ROTEIRO em texto "
    "organizado, com blocos rotulados (Gancho, Desenvolvimento, CTA) para o Bruno LER. Rode a skill "
    "humanizer nos roteiros. Pergunte qual ele escolhe. NÃO gere áudio nem post nesta etapa. "
    "ETAPA 2 — SCRIPT DE GRAVAÇÃO + ÁUDIO: quando ele escolher, monte o SCRIPT DE GRAVAÇÃO do roteiro "
    "escolhido = SOMENTE as frases que ele vai FALAR na câmera, uma por linha, na ordem. PROIBIDO no "
    "script de gravação: rótulos (Gancho/CTA/Desenvolvimento), rubricas ou direções de cena (entre [] "
    "ou ()), emoji, hashtag, marca de tempo. É só a fala, limpa. Defina NICHO (=tema) e DATA (hoje, "
    "AAAA-MM-DD); crie 'C04 Claude Obsidian/outputs/conteudo/<NICHO>/<DATA> — <TEMA>/' e salve nela: "
    "roteiro-reel.md (roteiro completo com estrutura) e script-gravacao.md (só as falas, limpo). "
    'Gere o áudio A PARTIR DO SCRIPT DE GRAVAÇÃO: uv run stella ear-prompter "<conteúdo de '
    'script-gravacao.md>" --saida "<pasta>/ear-prompter.mp3"; depois envie: uv run stella enviar-audio '
    '"<pasta>/ear-prompter.mp3". Mande no Telegram o script de gravação em texto e pergunte se APROVA. '
    "ETAPA 3 — FÁBRICA (só DEPOIS que ele aprovar): gere o post de feed companheiro — copy/legenda "
    "derivada do roteiro (rode humanizer), salva em post-feed.md com frontmatter 'marca: brunoe.santos', "
    "e um design_spec.json (briefing visual). A IMAGEM não é renderizada aqui (sem MCP/Paper neste modo): "
    "avise que ela fica pendente para render à parte. NÃO publique nada (Postiz desativado)."
)


@dataclass(frozen=True)
class TelegramSecrets:
    bot_token: str
    chat_id: str


@dataclass
class DaemonRuntime:
    started_at: float
    last_execution: str | None = None


def _as_record(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _append_log(log_path: Path, message: str) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().isoformat(timespec="seconds")
    with log_path.open("a", encoding="utf-8") as arquivo:
        arquivo.write(f"{timestamp} {message}\n")


def load_secrets(cofre_path: Path = COFRE_TELEGRAM) -> TelegramSecrets:
    data = json.loads(cofre_path.read_text(encoding="utf-8"))
    return TelegramSecrets(bot_token=str(data["bot_token"]), chat_id=str(data["chat_id"]))


def load_last_update_id(state_path: Path = DAEMON_STATE) -> int:
    if not state_path.exists():
        return 0
    data = json.loads(state_path.read_text(encoding="utf-8"))
    return int(data.get("last_update_id", 0))


def save_last_update_id(update_id: int, state_path: Path = DAEMON_STATE) -> None:
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps({"last_update_id": update_id}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def telegram_url(token: str, method: str) -> str:
    return f"https://api.telegram.org/bot{token}/{method}"


def split_telegram_text(text: str, limit: int = TELEGRAM_CHUNK_MAX) -> list[str]:
    if len(text) <= limit:
        return [text]

    partes: list[str] = []
    restante = text
    while len(restante) > limit:
        corte = restante.rfind("\n", 0, limit + 1)
        if corte <= 0:
            corte = limit
        partes.append(restante[:corte])
        restante = restante[corte:].lstrip("\n")
    if restante:
        partes.append(restante)
    return partes


def send_message(token: str, chat_id: str, text: str) -> None:
    for parte in split_telegram_text(text):
        httpx.post(
            telegram_url(token, "sendMessage"),
            json={"chat_id": chat_id, "text": parte},
            timeout=20,
        ).raise_for_status()


def send_chat_action(token: str, chat_id: str, action: str = "typing") -> None:
    httpx.post(
        telegram_url(token, "sendChatAction"),
        json={"chat_id": chat_id, "action": action},
        timeout=10,
    ).raise_for_status()


def get_updates(token: str, offset: int) -> list[dict[str, object]]:
    response = httpx.get(
        telegram_url(token, "getUpdates"),
        params={"offset": offset, "timeout": 50},
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    updates = data.get("result", []) if isinstance(data, dict) else []
    return [update for update in updates if isinstance(update, dict)]


def baixar_arquivo_voz(token: str, file_id: str, destino_dir: Path) -> Path:
    info = httpx.get(telegram_url(token, "getFile"), params={"file_id": file_id}, timeout=30)
    info.raise_for_status()
    data = info.json()
    file_path = str(_as_record(data.get("result")).get("file_path", ""))
    if not file_path:
        raise ValueError("getFile sem file_path na resposta")

    destino = destino_dir / (Path(file_path).name or "voz.oga")
    audio = httpx.get(f"https://api.telegram.org/file/bot{token}/{file_path}", timeout=120)
    audio.raise_for_status()
    destino.write_bytes(audio.content)
    return destino


def transcrever_audio_padrao(caminho: Path) -> str:
    from stella.corpo.gravador import transcrever_comando

    return transcrever_comando(caminho)


def sintetizar_fala_padrao(texto: str, destino: Path) -> Path:
    from stella.corpo.voz import sintetizar

    return sintetizar(texto, destino)


def send_voice(token: str, chat_id: str, caminho: Path) -> None:
    with caminho.open("rb") as audio:
        httpx.post(
            telegram_url(token, "sendVoice"),
            data={"chat_id": chat_id},
            files={"voice": (caminho.name, audio, "audio/mpeg")},
            timeout=60,
        ).raise_for_status()


def _selecionar_modelo(texto: str) -> tuple[str, str]:
    """Sonnet por padrão; a frase 'Stella eu preciso do Opus' ativa o Opus
    só naquela mensagem (e a frase é removida do texto enviado ao Claude)."""
    if GATILHO_OPUS.search(texto):
        limpo = GATILHO_OPUS.sub(" ", texto).strip()
        return MODELO_OPUS, (limpo or texto)
    return MODELO_PADRAO, texto


def _ler_sessao() -> str | None:
    try:
        if SESSION_STATE.exists():
            sid = json.loads(SESSION_STATE.read_text(encoding="utf-8")).get("session_id")
            return sid if isinstance(sid, str) and sid else None
    except Exception:
        return None
    return None


def _salvar_sessao(session_id: str | None) -> None:
    if not session_id:
        return
    try:
        SESSION_STATE.write_text(json.dumps({"session_id": session_id}), encoding="utf-8")
    except Exception:
        pass


def resetar_sessao() -> None:
    try:
        SESSION_STATE.unlink(missing_ok=True)
    except Exception:
        pass


def _conteudo_ativo() -> bool:
    """True se o modo conteúdo está ligado e dentro do TTL (sticky entre mensagens)."""
    try:
        if CONTEUDO_STATE.exists():
            data = json.loads(CONTEUDO_STATE.read_text(encoding="utf-8"))
            desde = data.get("desde")
            if data.get("ativo") and isinstance(desde, str):
                dt = datetime.fromisoformat(desde)
                if datetime.now(dt.tzinfo) - dt <= timedelta(minutes=CONTEUDO_TTL_MIN):
                    return True
    except Exception:
        return False
    return False


def _ativar_conteudo(modo: str = "reel") -> None:
    try:
        CONTEUDO_STATE.write_text(
            json.dumps(
                {"ativo": True, "desde": datetime.now().astimezone().isoformat(), "modo": modo}
            ),
            encoding="utf-8",
        )
    except Exception:
        pass


def _modo_sticky() -> str | None:
    """Modo de conteúdo guardado no estado sticky ('carrossel'|'reel'), ou None."""
    try:
        if CONTEUDO_STATE.exists():
            data = json.loads(CONTEUDO_STATE.read_text(encoding="utf-8"))
            if data.get("ativo"):
                return str(data.get("modo", "reel"))
    except Exception:
        return None
    return None


def _desativar_conteudo() -> None:
    try:
        CONTEUDO_STATE.unlink(missing_ok=True)
    except Exception:
        pass


def _escolher_modo(texto: str, modo_sticky: str | None) -> str | None:
    """Decide o modo de conteúdo: 'carrossel', 'reel' ou None (chat normal).

    Carrossel tem prioridade sobre o gatilho genérico de conteúdo; um follow-up
    sem gatilho herda o modo sticky.
    """
    if GATILHO_CARROSSEL.search(texto):
        return "carrossel"
    if GATILHO_CONTEUDO.search(texto):
        return "reel"
    return modo_sticky


def _rodar_claude_json(args: list[str]) -> tuple[int, str, str]:
    try:
        r = subprocess.run(
            args,
            cwd=CLAUDE_CWD,
            timeout=600,
            capture_output=True,
            text=True,
            encoding="utf-8",
            shell=False,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return (-1, "", "timeout")
    return (r.returncode, r.stdout or "", r.stderr or "")


def _extrair_resposta(stdout: str, salvar_sessao: bool) -> str:
    """Extrai o texto do JSON do claude -p; opcionalmente persiste o session_id."""
    try:
        data = json.loads(stdout)
        if isinstance(data, dict):
            if salvar_sessao:
                _salvar_sessao(data.get("session_id"))
            res = data.get("result")
            if isinstance(res, str) and res.strip():
                return res.strip()
    except (json.JSONDecodeError, ValueError):
        pass
    return stdout.strip() or "Concluído, sem saída de texto."


def _args_claude(
    claude_bin: str,
    texto: str,
    *,
    modelo: str | None = None,
    resume: str | None = None,
    mcp_on: bool = False,
    persona: str | None = None,
) -> list[str]:
    """Monta os argumentos do `claude -p`. resume herda modelo/persona da sessão."""
    args = [claude_bin, "-p", texto]
    if resume:
        args += ["--resume", resume]
    elif modelo:
        args += ["--model", modelo]
    if not mcp_on:
        args.append("--strict-mcp-config")  # chat rápido: sem carregar MCP
    if persona:
        args += ["--append-system-prompt", persona]
    args += ["--output-format", "json"]
    return args


def _resultado(code: int, out: str, err: str, *, salvar: bool) -> str:
    if code == -1:
        return "Senhor, a execução passou do tempo limite e foi interrompida."
    if code != 0:
        return f"Senhor, o Claude retornou erro: {err.strip()[:500] or 'sem detalhes'}"
    return _extrair_resposta(out, salvar_sessao=salvar)


def executar_claude(texto: str) -> str:
    # No Windows o `claude` do npm e um shim .cmd/.ps1; resolvemos via shutil.which.
    modelo_sel, texto = _selecionar_modelo(texto)
    claude_bin = shutil.which("claude") or "claude"

    conteudo_ja_ativo = _conteudo_ativo()
    modo = _escolher_modo(texto, _modo_sticky() if conteudo_ja_ativo else None)
    intent_novo = bool(GATILHO_CARROSSEL.search(texto) or GATILHO_CONTEUDO.search(texto))
    nova_solicitacao = intent_novo and bool(_RE_ACAO_NOVA.search(texto))

    # Opus avulso ("preciso do opus") fora do modo conteúdo: chamada única, sem sessão.
    if modelo_sel == MODELO_OPUS and modo is None:
        code, out, err = _rodar_claude_json(
            _args_claude(claude_bin, texto, modelo=MODELO_OPUS, persona=PERSONA_STELLA)
        )
        return _resultado(code, out, err, salvar=False)

    if modo is not None:
        # Conteúdo: Opus + persona do modo, MCP OFF (rápido). Usa skills
        # (notebooklm, humanizer), WebSearch e os comandos `stella` da fábrica.
        modelo = MODELO_OPUS
        mcp_on = False
        extra = PERSONA_CARROSSEL if modo == "carrossel" else PERSONA_CONTEUDO
        persona = PERSONA_STELLA + "\n\n" + extra
        if nova_solicitacao:
            resetar_sessao()  # pedido NOVO → sessão limpa (esquece o tema anterior)
        _ativar_conteudo(modo)  # renova o TTL sticky e guarda o modo
    else:
        modelo = MODELO_PADRAO
        mcp_on = False
        persona = PERSONA_STELLA

    sessao = _ler_sessao()
    if sessao:
        code, out, err = _rodar_claude_json(
            _args_claude(claude_bin, texto, resume=sessao, mcp_on=mcp_on)
        )
        if code == 0:
            return _extrair_resposta(out, salvar_sessao=True)
        if code == -1:
            return "Senhor, a execução passou do tempo limite e foi interrompida."
        # resume falhou (sessão expirada/inválida): recomeça do zero abaixo.

    code, out, err = _rodar_claude_json(
        _args_claude(claude_bin, texto, modelo=modelo, mcp_on=mcp_on, persona=persona)
    )
    return _resultado(code, out, err, salvar=True)


def _status_text(runtime: DaemonRuntime) -> str:
    uptime_s = int(time.time() - runtime.started_at)
    minutos, segundos = divmod(uptime_s, 60)
    horas, minutos = divmod(minutos, 60)
    ultima = runtime.last_execution or "nenhuma ainda"
    return (
        "📊 Status da Stella\n"
        "\n"
        f"⏱ Online há {horas}h{minutos:02d}m{segundos:02d}s\n"
        f"⚙️ Última execução: {ultima}\n"
        "🧠 Cérebro: Claude Code | 🎤 Voz: ouve e fala"
    )


def _texto_de_voz(
    message: dict[str, object],
    secrets: TelegramSecrets,
    *,
    transcrever_audio: Callable[[Path], str],
    log_path: Path,
) -> str | None:
    """Baixa e transcreve voice/audio da mensagem; None se nao houver ou falhar."""
    midia = _as_record(message.get("voice")) or _as_record(message.get("audio"))
    file_id = midia.get("file_id")
    if not isinstance(file_id, str) or not file_id:
        return None

    try:
        send_chat_action(secrets.bot_token, secrets.chat_id)
    except Exception as exc:
        _append_log(log_path, f"sendChatAction falhou: {type(exc).__name__}")

    try:
        with tempfile.TemporaryDirectory() as tmp:
            caminho = baixar_arquivo_voz(secrets.bot_token, file_id, Path(tmp))
            return transcrever_audio(caminho).strip()
    except Exception as exc:
        _append_log(log_path, f"falha ao transcrever voz: {type(exc).__name__}")
        send_message(
            secrets.bot_token,
            secrets.chat_id,
            "Senhor, não consegui processar esse áudio. Pode tentar de novo ou digitar?",
        )
        return None


def _responder_com_voz(
    resposta: str,
    secrets: TelegramSecrets,
    *,
    sintetizar_fala: Callable[[str, Path], Path],
    log_path: Path,
) -> bool:
    """Sintetiza e envia a resposta falada. True se enviou; False em falha (chamador faz texto)."""
    try:
        with tempfile.TemporaryDirectory() as tmp:
            caminho = sintetizar_fala(resposta, Path(tmp) / "resposta.mp3")
            send_voice(secrets.bot_token, secrets.chat_id, caminho)
        return True
    except Exception as exc:
        _append_log(log_path, f"falha ao sintetizar voz: {type(exc).__name__}")
        return False


def process_update(
    update: dict[str, object],
    secrets: TelegramSecrets,
    runtime: DaemonRuntime,
    *,
    run_claude: Callable[[str], str] = executar_claude,
    transcrever_audio: Callable[[Path], str] = transcrever_audio_padrao,
    sintetizar_fala: Callable[[str, Path], Path] = sintetizar_fala_padrao,
    log_path: Path = DAEMON_LOG,
) -> None:
    message = _as_record(update.get("message"))
    chat = _as_record(message.get("chat"))
    chat_id = str(chat.get("id", ""))

    if chat_id != secrets.chat_id:
        if chat_id:
            _append_log(log_path, f"chat nao autorizado ignorado chat_id={chat_id}")
        return

    veio_de_voz = False
    texto = message.get("text")
    if not isinstance(texto, str) or not texto.strip():
        texto = _texto_de_voz(
            message, secrets, transcrever_audio=transcrever_audio, log_path=log_path
        )
        veio_de_voz = texto is not None
        if not texto:
            if veio_de_voz:
                send_message(
                    secrets.bot_token,
                    secrets.chat_id,
                    "Senhor, o áudio veio vazio ou sem fala clara.",
                )
            return

    texto_limpo = texto.strip()
    if texto_limpo.startswith("/ping"):
        agora = datetime.now()
        card = (
            "⚡ Stella online_\n"
            "\n"
            "🧠 Cérebro: Claude Code\n"
            "📡 Corpo: daemon Telegram\n"
            "🎤 Voz: ouve e fala (whisper + edge-tts)\n"
            f"🕐 {agora:%d/%m/%Y %H:%M:%S}"
        )
        send_message(secrets.bot_token, secrets.chat_id, card)
        return

    if texto_limpo.startswith("/status"):
        send_message(secrets.bot_token, secrets.chat_id, _status_text(runtime))
        return

    if texto_limpo.startswith("/novo"):
        resetar_sessao()
        _desativar_conteudo()
        send_message(
            secrets.bot_token,
            secrets.chat_id,
            "🧠 Memória da conversa reiniciada. Começamos do zero, Senhor.",
        )
        return

    try:
        send_chat_action(secrets.bot_token, secrets.chat_id)
    except Exception as exc:
        _append_log(log_path, f"sendChatAction falhou: {type(exc).__name__}")

    resposta = run_claude(texto_limpo)
    runtime.last_execution = datetime.now().isoformat(timespec="seconds")
    # No modo conteúdo a resposta vai em TEXTO (pra ler), nunca auto-voz: o único
    # áudio é o ear-prompter limpo, enviado à parte. Fora dele, áudio→áudio.
    if veio_de_voz and not _conteudo_ativo():
        enviou_voz = _responder_com_voz(
            resposta, secrets, sintetizar_fala=sintetizar_fala, log_path=log_path
        )
        if not enviou_voz:
            send_message(secrets.bot_token, secrets.chat_id, resposta)
        return
    send_message(secrets.bot_token, secrets.chat_id, resposta)


def run_daemon(
    *,
    cofre_path: Path = COFRE_TELEGRAM,
    state_path: Path = DAEMON_STATE,
    log_path: Path = DAEMON_LOG,
) -> None:
    secrets = load_secrets(cofre_path)
    runtime = DaemonRuntime(started_at=time.time())
    last_update_id = load_last_update_id(state_path)
    _append_log(log_path, "daemon iniciado")

    while True:
        try:
            updates = get_updates(secrets.bot_token, last_update_id + 1)
            for update in updates:
                update_id = update.get("update_id")
                if not isinstance(update_id, int):
                    continue
                last_update_id = update_id
                save_last_update_id(update_id, state_path)
                try:
                    process_update(update, secrets, runtime, log_path=log_path)
                except Exception as exc:
                    _append_log(log_path, f"erro em update {update_id}: {type(exc).__name__}")
        except KeyboardInterrupt:
            _append_log(log_path, "daemon encerrado por KeyboardInterrupt")
            raise
        except Exception as exc:
            _append_log(log_path, f"falha de polling: {type(exc).__name__}")
            time.sleep(10)
