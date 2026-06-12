from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import httpx

VAULT_DIR = Path("D:/VortexBrain00/bssurf00")
COFRES_DIR = Path("D:/VortexBrain00/.secrets")
COFRE_TELEGRAM = COFRES_DIR / "telegram.json"
SECURITY_LOG_REL = "C04 Claude Obsidian/logs e memória/security-log.md"

PASTAS_RAIZ = [
    "A00 Inbox",
    "A01 Processamento",
    "A02 Tópicos Para links",
    "A03 Banco de Imagens",
    "A04 Notas diárias - Pensamentos",
    "A05 Backlog",
    "B01 Projetos",
    "B02 Recursos",
    "B03 Arquivos",
    "B04 Sistemas",
    "C01 Diretrizes",
    "C02 Readwise",
    "C03 Book database",
    "C04 Claude Obsidian",
]

ARQUIVOS_CRITICOS = [
    "C04 Claude Obsidian/logs e memória/Stella Memory.md",
    "C04 Claude Obsidian/Comandos e Diretrizes/Diretrizes Gerais.md",
    "C04 Claude Obsidian/Comandos e Diretrizes/Plano de Segurança Diário.md",
]

COFRES = ["telegram.json", "brevo.json"]


@dataclass
class Relatorio:
    criticos: list[str] = field(default_factory=list)
    atencoes: list[str] = field(default_factory=list)
    infos: list[str] = field(default_factory=list)

    @property
    def status(self) -> str:
        if self.criticos:
            return "❌ Problema"
        if self.atencoes:
            return "⚠️ Atenção"
        return "✅ OK"

    @property
    def problemas(self) -> list[str]:
        return self.criticos + self.atencoes


def verificar_vault(relatorio: Relatorio, vault_dir: Path = VAULT_DIR) -> None:
    if not vault_dir.is_dir():
        relatorio.criticos.append(f"Vault inacessível: {vault_dir}")
        return
    faltando = [pasta for pasta in PASTAS_RAIZ if not (vault_dir / pasta).is_dir()]
    for pasta in faltando:
        relatorio.criticos.append(f"Pasta raiz sumiu: {pasta}")
    relatorio.infos.append(
        f"Vault: {len(PASTAS_RAIZ) - len(faltando)}/{len(PASTAS_RAIZ)} pastas raiz"
    )


def verificar_arquivos_criticos(relatorio: Relatorio, vault_dir: Path = VAULT_DIR) -> None:
    for rel in ARQUIVOS_CRITICOS:
        caminho = vault_dir / rel
        try:
            conteudo = caminho.read_text(encoding="utf-8")
        except FileNotFoundError:
            relatorio.criticos.append(f"Arquivo crítico sumiu: {caminho.name}")
            continue
        except Exception:
            relatorio.criticos.append(f"Arquivo crítico ilegível: {caminho.name}")
            continue
        if not conteudo.strip():
            relatorio.criticos.append(f"Arquivo crítico vazio: {caminho.name}")


def verificar_cofres(relatorio: Relatorio, cofres_dir: Path = COFRES_DIR) -> None:
    for nome in COFRES:
        caminho = cofres_dir / nome
        try:
            json.loads(caminho.read_text(encoding="utf-8"))
        except FileNotFoundError:
            relatorio.criticos.append(f"Cofre sumiu: {nome}")
        except Exception:
            relatorio.criticos.append(f"Cofre corrompido (JSON inválido): {nome}")


def contar_daemon_rodando() -> int:
    """Conta processos python rodando `stella daemon` via PowerShell (Windows)."""
    comando = (
        "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
        "Where-Object { $_.CommandLine -match 'stella' -and $_.CommandLine -match 'daemon' } | "
        "Measure-Object | Select-Object -ExpandProperty Count"
    )
    result = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", comando],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    try:
        return int(result.stdout.strip() or 0)
    except ValueError:
        return 0


def verificar_daemon(relatorio: Relatorio, contar: int | None = None) -> None:
    total = contar_daemon_rodando() if contar is None else contar
    if total == 0:
        relatorio.atencoes.append("Daemon Telegram PARADO (Stella sem ouvidos)")
    else:
        relatorio.infos.append("Daemon Telegram: rodando")


def notas_alteradas_fora_de_c04(
    vault_dir: Path = VAULT_DIR, horas: float = 24.0, agora: float | None = None
) -> int:
    """Conta .md alterados nas últimas N horas fora da zona autônoma C04 (informativo)."""
    referencia = (agora if agora is not None else time.time()) - horas * 3600
    total = 0
    for arquivo in vault_dir.rglob("*.md"):
        rel = arquivo.relative_to(vault_dir)
        if rel.parts and rel.parts[0] == "C04 Claude Obsidian":
            continue
        try:
            if arquivo.stat().st_mtime >= referencia:
                total += 1
        except OSError:
            continue
    return total


def executar_verificacao(vault_dir: Path = VAULT_DIR, cofres_dir: Path = COFRES_DIR) -> Relatorio:
    relatorio = Relatorio()
    verificar_vault(relatorio, vault_dir)
    if vault_dir.is_dir():
        verificar_arquivos_criticos(relatorio, vault_dir)
        alteradas = notas_alteradas_fora_de_c04(vault_dir)
        relatorio.infos.append(f"Notas alteradas fora de C04 (24h): {alteradas}")
    verificar_cofres(relatorio, cofres_dir)
    verificar_daemon(relatorio)
    return relatorio


def registrar_log(relatorio: Relatorio, vault_dir: Path = VAULT_DIR) -> Path:
    """Anexa o resultado ao security-log.md no formato do protocolo do plano."""
    log_path = vault_dir / SECURITY_LOG_REL
    log_path.parent.mkdir(parents=True, exist_ok=True)
    agora = datetime.now()
    problemas = "; ".join(relatorio.problemas) or "nenhum"
    acao = "alertado via Telegram" if relatorio.problemas else "nenhuma necessária"
    entrada = (
        f"\n## [{agora:%Y-%m-%d %H:%M}] Verificação Diária (v2 determinística)\n"
        f"- Status geral: {relatorio.status}\n"
        f"- Itens com problema: {problemas}\n"
        f"- Ação tomada: {acao}\n"
        f"- Detalhes: {'; '.join(relatorio.infos)}\n"
    )
    with log_path.open("a", encoding="utf-8") as arquivo:
        arquivo.write(entrada)
    return log_path


def montar_card(relatorio: Relatorio) -> str:
    agora = datetime.now()
    linhas = [f"🛡 Segurança diária | {relatorio.status}", ""]
    linhas.extend(f"🚨 {item}" for item in relatorio.criticos)
    linhas.extend(f"⚠️ {item}" for item in relatorio.atencoes)
    linhas.extend(f"✔️ {item}" for item in relatorio.infos)
    linhas.append(f"🕐 {agora:%d/%m/%Y %H:%M}")
    return "\n".join(linhas)


def avisar_telegram(texto: str, cofre_path: Path = COFRE_TELEGRAM) -> None:
    cofre = json.loads(cofre_path.read_text(encoding="utf-8"))
    httpx.post(
        f"https://api.telegram.org/bot{cofre['bot_token']}/sendMessage",
        json={"chat_id": str(cofre["chat_id"]), "text": texto},
        timeout=20,
    ).raise_for_status()


def rodar_seguranca_diaria(vault_dir: Path = VAULT_DIR, cofres_dir: Path = COFRES_DIR) -> Relatorio:
    relatorio = executar_verificacao(vault_dir, cofres_dir)
    registrar_log(relatorio, vault_dir)
    try:
        avisar_telegram(montar_card(relatorio), cofres_dir / "telegram.json")
    except Exception:
        # Sem Telegram o log no vault ainda registra; nao derruba a rotina.
        pass
    return relatorio
