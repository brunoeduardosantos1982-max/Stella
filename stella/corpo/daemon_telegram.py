from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import httpx

COFRE_TELEGRAM = Path("D:/VortexBrain00/.secrets/telegram.json")
DAEMON_STATE = Path("D:/VortexBrain00/.secrets/daemon_state.json")
DAEMON_LOG = Path("D:/VortexBrain00/.secrets/daemon.log")
CLAUDE_CWD = Path("D:/VortexBrain00")
TELEGRAM_CHUNK_MAX = 4000


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


def executar_claude(texto: str) -> str:
    # No Windows o `claude` do npm e um shim .cmd/.ps1; CreateProcess nao resolve
    # esses sufixos sem o caminho completo, entao resolvemos via shutil.which.
    claude_bin = shutil.which("claude") or "claude"
    try:
        result = subprocess.run(
            [claude_bin, "-p", texto, "--output-format", "text"],
            cwd=CLAUDE_CWD,
            timeout=600,
            capture_output=True,
            text=True,
            encoding="utf-8",
            shell=False,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return "Senhor, a execução passou do tempo limite e foi interrompida."

    if result.returncode == 0:
        saida = result.stdout.strip()
        return saida or "Concluído, sem saída de texto."

    erro = result.stderr.strip()[:500]
    return f"Senhor, o Claude retornou erro: {erro or 'sem detalhes'}"


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
        "🧠 Cérebro: Claude Code | 🎤 Voz: ativa"
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


def process_update(
    update: dict[str, object],
    secrets: TelegramSecrets,
    runtime: DaemonRuntime,
    *,
    run_claude: Callable[[str], str] = executar_claude,
    transcrever_audio: Callable[[Path], str] = transcrever_audio_padrao,
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
            "🎤 Voz: ativa (whisper local)\n"
            f"🕐 {agora:%d/%m/%Y %H:%M:%S}"
        )
        send_message(secrets.bot_token, secrets.chat_id, card)
        return

    if texto_limpo.startswith("/status"):
        send_message(secrets.bot_token, secrets.chat_id, _status_text(runtime))
        return

    try:
        send_chat_action(secrets.bot_token, secrets.chat_id)
    except Exception as exc:
        _append_log(log_path, f"sendChatAction falhou: {type(exc).__name__}")

    resposta = run_claude(texto_limpo)
    runtime.last_execution = datetime.now().isoformat(timespec="seconds")
    if veio_de_voz:
        resposta = f'🎤 Entendi: "{texto_limpo}"\n\n{resposta}'
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
