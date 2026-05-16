import json
from datetime import datetime

from stella.infra.usage_tracker import UsageRecord, UsageTracker


def test_record_grava_linha_jsonl(tmp_path):
    tracker = UsageTracker(usage_dir=tmp_path)
    tracker.record(
        UsageRecord(
            momento=datetime(2026, 5, 16, 10, 30),
            provider="gemma_nvidia",
            modelo="google/gemma-4-31b-it",
            tokens_input=120,
            tokens_output=45,
            custo_usd=0.0,
        )
    )
    arquivo = tmp_path / "2026-05-16.jsonl"
    assert arquivo.exists()
    linha = json.loads(arquivo.read_text(encoding="utf-8").strip())
    assert linha["provider"] == "gemma_nvidia"
    assert linha["tokens_input"] == 120
    assert linha["tokens_output"] == 45
    assert linha["custo_usd"] == 0.0


def test_records_no_mesmo_dia_acumulam(tmp_path):
    tracker = UsageTracker(usage_dir=tmp_path)
    for i in range(3):
        tracker.record(
            UsageRecord(
                momento=datetime(2026, 5, 16, 10, i),
                provider="anthropic",
                modelo="claude-sonnet-4-6",
                tokens_input=100,
                tokens_output=50,
                custo_usd=0.001,
            )
        )
    arquivo = tmp_path / "2026-05-16.jsonl"
    linhas = arquivo.read_text(encoding="utf-8").strip().split("\n")
    assert len(linhas) == 3


def test_total_do_dia(tmp_path):
    tracker = UsageTracker(usage_dir=tmp_path)
    for _ in range(2):
        tracker.record(
            UsageRecord(
                momento=datetime(2026, 5, 16, 10, 0),
                provider="anthropic",
                modelo="claude-sonnet-4-6",
                tokens_input=100,
                tokens_output=50,
                custo_usd=0.0015,
            )
        )
    total = tracker.total_do_dia(datetime(2026, 5, 16))
    assert total["chamadas"] == 2
    assert total["tokens_input"] == 200
    assert total["tokens_output"] == 100
    assert abs(total["custo_usd"] - 0.003) < 1e-9


def test_total_do_dia_sem_arquivo_retorna_zeros(tmp_path):
    tracker = UsageTracker(usage_dir=tmp_path)
    total = tracker.total_do_dia(datetime(2026, 5, 16))
    assert total == {"chamadas": 0, "tokens_input": 0, "tokens_output": 0, "custo_usd": 0.0}
