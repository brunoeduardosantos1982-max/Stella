"""Testes do adapter Higgsfield (cliente CLI `hf` + fake)."""

import subprocess

import pytest

from stella.adapters.higgsfield.base import HiggsFieldError
from stella.adapters.higgsfield.client import CliHiggsFieldClient
from stella.adapters.higgsfield.fake import FakeHiggsField

# --- Fake (inalterado) ---


def test_fake_retorna_url_deterministica() -> None:
    fake = FakeHiggsField()
    url = fake.generate_image("Bruno em escritório tech")
    assert url.startswith("https://fake.higgsfield.ai/")
    assert url.endswith(".jpg")


def test_fake_registra_calls() -> None:
    fake = FakeHiggsField()
    fake.generate_image("cena 1")
    fake.generate_image("cena 2", soul_id="soul-abc")
    assert len(fake.calls) == 2
    assert fake.calls[0]["prompt"] == "cena 1"
    assert fake.calls[1]["soul_id"] == "soul-abc"


def test_fake_url_diferente_para_prompts_diferentes() -> None:
    fake = FakeHiggsField()
    assert fake.generate_image("cena A") != fake.generate_image("cena B")


# --- Cliente CLI ---


def _runner(returncode: int = 0, stdout: str = "", stderr: str = ""):
    """Fabrica um runner injetável que registra os args recebidos."""
    captura: dict[str, object] = {}

    def run(args: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
        captura["args"] = args
        captura["timeout"] = timeout
        return subprocess.CompletedProcess(args, returncode, stdout, stderr)

    run.captura = captura  # type: ignore[attr-defined]
    return run


def test_monta_comando_hf_com_modelo_e_params() -> None:
    runner = _runner(stdout='{"results":[{"url":"https://cdn.higgsfield.ai/a/x.jpg"}]}')
    client = CliHiggsFieldClient(hf_path="hf", runner=runner)
    client.generate_image("Bruno tech office")
    args = runner.captura["args"]  # type: ignore[attr-defined]
    assert args[:4] == ["hf", "generate", "create", "text2image_soul_v2"]
    assert "--prompt" in args and "Bruno tech office" in args
    assert "--aspect_ratio" in args and "1:1" in args
    assert "--quality" in args and "2k" in args
    assert "--wait" in args
    assert "--json" in args


def test_retorna_url_extraida_do_json() -> None:
    runner = _runner(stdout='{"results":[{"url":"https://cdn.higgsfield.ai/a/x.jpg"}]}')
    client = CliHiggsFieldClient(hf_path="hf", runner=runner)
    assert client.generate_image("cena") == "https://cdn.higgsfield.ai/a/x.jpg"


def test_extrai_url_em_shape_aninhado_diferente() -> None:
    stdout = '[{"id":"job1","status":"completed","raw":{"image":"https://cdn.higgsfield.ai/b/y.png?sig=1"}}]'
    client = CliHiggsFieldClient(hf_path="hf", runner=_runner(stdout=stdout))
    assert client.generate_image("cena") == "https://cdn.higgsfield.ai/b/y.png?sig=1"


def test_aspect_ratio_e_quality_customizados_vao_no_comando() -> None:
    runner = _runner(stdout='{"url":"https://cdn.higgsfield.ai/c/z.webp"}')
    client = CliHiggsFieldClient(hf_path="hf", runner=runner, aspect_ratio="3:4", quality="1.5k")
    client.generate_image("cena")
    args = runner.captura["args"]  # type: ignore[attr-defined]
    assert "3:4" in args
    assert "1.5k" in args


def test_aspect_ratio_invalido_levanta_error() -> None:
    with pytest.raises(HiggsFieldError, match="aspect_ratio"):
        CliHiggsFieldClient(hf_path="hf", runner=_runner(), aspect_ratio="4:5")


def test_quality_invalida_levanta_error() -> None:
    with pytest.raises(HiggsFieldError, match="quality"):
        CliHiggsFieldClient(hf_path="hf", runner=_runner(), quality="8k")


def test_soul_id_ainda_nao_suportado_levanta_error() -> None:
    client = CliHiggsFieldClient(hf_path="hf", runner=_runner())
    with pytest.raises(HiggsFieldError, match="soul-id create"):
        client.generate_image("cena", soul_id="ref-123")


def test_exit_nao_zero_levanta_error_com_stderr() -> None:
    client = CliHiggsFieldClient(hf_path="hf", runner=_runner(returncode=1, stderr="boom"))
    with pytest.raises(HiggsFieldError, match="boom"):
        client.generate_image("cena")


def test_json_sem_url_levanta_error() -> None:
    client = CliHiggsFieldClient(hf_path="hf", runner=_runner(stdout='{"status":"completed"}'))
    with pytest.raises(HiggsFieldError, match="sem URL"):
        client.generate_image("cena")


def test_binario_hf_ausente_levanta_error() -> None:
    def run(args: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
        raise FileNotFoundError("hf")

    client = CliHiggsFieldClient(hf_path="hf", runner=run)
    with pytest.raises(HiggsFieldError, match="não encontrado"):
        client.generate_image("cena")


def test_timeout_levanta_error() -> None:
    def run(args: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(args, timeout)

    client = CliHiggsFieldClient(hf_path="hf", runner=run)
    with pytest.raises(HiggsFieldError, match="tempo"):
        client.generate_image("cena")
