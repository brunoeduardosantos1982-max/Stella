"""Testes do adapter Higgsfield."""

import httpx
import pytest

from stella.adapters.higgsfield.base import HiggsFieldError
from stella.adapters.higgsfield.client import HttpHiggsFieldClient
from stella.adapters.higgsfield.fake import FakeHiggsField


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
    url1 = fake.generate_image("cena A")
    url2 = fake.generate_image("cena B")
    assert url1 != url2


def _mock_transport(responses: list[tuple[int, dict]]) -> httpx.MockTransport:
    """Helper: cria MockTransport com sequência de respostas."""
    queue = list(responses)

    def handler(request: httpx.Request) -> httpx.Response:
        status, body = queue.pop(0)
        return httpx.Response(status, json=body)

    return httpx.MockTransport(handler)


def test_client_retorna_url_quando_job_completa() -> None:
    transport = _mock_transport(
        [
            (200, {"job_id": "job-123"}),
            (
                200,
                {
                    "status": "completed",
                    "image_url": "https://cdn.higgsfield.ai/img/abc.jpg",
                },
            ),
        ]
    )
    client = HttpHiggsFieldClient(token="tok", _transport=transport)
    url = client.generate_image("Bruno tech office")
    assert url == "https://cdn.higgsfield.ai/img/abc.jpg"


def test_client_levanta_error_quando_job_falha() -> None:
    transport = _mock_transport(
        [
            (200, {"job_id": "job-456"}),
            (200, {"status": "failed", "error": "modelo indisponível"}),
        ]
    )
    client = HttpHiggsFieldClient(token="tok", _transport=transport)
    with pytest.raises(HiggsFieldError, match="modelo indisponível"):
        client.generate_image("cena")


def test_client_levanta_error_em_status_http_erro() -> None:
    transport = _mock_transport([(401, {"message": "Unauthorized"})])
    client = HttpHiggsFieldClient(token="tok-invalido", _transport=transport)
    with pytest.raises(HiggsFieldError, match="Higgsfield HTTP 401"):
        client.generate_image("cena")
