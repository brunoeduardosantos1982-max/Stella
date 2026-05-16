import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

# Preços por 1M tokens (em USD) — fonte da verdade central
PRECOS_USD_POR_MILHAO: dict[str, dict[str, float]] = {
    "google/gemma-4-31b-it": {"input": 0.0, "output": 0.0},
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0},
    "claude-opus-4-7": {"input": 15.0, "output": 75.0},
}


@dataclass
class UsageRecord:
    momento: datetime
    provider: str
    modelo: str
    tokens_input: int
    tokens_output: int
    custo_usd: float


class UsageTracker:
    """Registra cada chamada LLM em JSONL diário para auditoria e budget."""

    def __init__(self, usage_dir: Path | None = None) -> None:
        if usage_dir is None:
            usage_dir = Path.home() / ".stella" / "usage"
        usage_dir.mkdir(parents=True, exist_ok=True)
        self._dir = usage_dir

    def record(self, r: UsageRecord) -> None:
        arquivo = self._dir / f"{r.momento.strftime('%Y-%m-%d')}.jsonl"
        linha = json.dumps(
            {
                "momento": r.momento.isoformat(),
                "provider": r.provider,
                "modelo": r.modelo,
                "tokens_input": r.tokens_input,
                "tokens_output": r.tokens_output,
                "custo_usd": r.custo_usd,
            },
            ensure_ascii=False,
        )
        with arquivo.open("a", encoding="utf-8") as fh:
            fh.write(linha + "\n")

    def total_do_dia(self, dia: datetime) -> dict[str, int | float]:
        arquivo = self._dir / f"{dia.strftime('%Y-%m-%d')}.jsonl"
        if not arquivo.exists():
            return {"chamadas": 0, "tokens_input": 0, "tokens_output": 0, "custo_usd": 0.0}
        chamadas = 0
        tokens_in = 0
        tokens_out = 0
        custo = 0.0
        for linha in arquivo.read_text(encoding="utf-8").splitlines():
            if not linha.strip():
                continue
            d = json.loads(linha)
            chamadas += 1
            tokens_in += d["tokens_input"]
            tokens_out += d["tokens_output"]
            custo += d["custo_usd"]
        return {
            "chamadas": chamadas,
            "tokens_input": tokens_in,
            "tokens_output": tokens_out,
            "custo_usd": custo,
        }


def estimar_custo(modelo: str, tokens_input: int, tokens_output: int) -> float:
    """Calcula custo em USD para um modelo conhecido. 0.0 para modelos free."""
    p = PRECOS_USD_POR_MILHAO.get(modelo)
    if p is None:
        return 0.0
    return (tokens_input / 1_000_000.0) * p["input"] + (tokens_output / 1_000_000.0) * p["output"]
