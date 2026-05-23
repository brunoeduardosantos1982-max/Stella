import json

import httpx
import pytest

from stella.adapters.postiz.base import PostizAgendamento, PostizError, PostizMidia
from stella.adapters.postiz.client import HttpPostizClient


def _client(handler: object) -> HttpPostizClient:
    transport = httpx.MockTransport(handler)  # type: ignore[arg-type]
    return HttpPostizClient(token="tok", http=httpx.Client(transport=transport))


def test_upload_imagem_envia_e_devolve_midia() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/upload")
        assert request.headers["Authorization"] == "tok"
        return httpx.Response(200, json={"id": "img-9", "path": "/up/x.png"})

    client = _client(handler)
    midia = client.upload_imagem(b"dados", "x.png")
    assert midia == PostizMidia(id="img-9", path="/up/x.png")


def test_upload_imagem_http_erro_levanta_postiz_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="erro interno")

    client = _client(handler)
    with pytest.raises(PostizError):
        client.upload_imagem(b"dados", "x.png")


def test_upload_imagem_resposta_sem_id_levanta() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"algo": "errado"})

    client = _client(handler)
    with pytest.raises(PostizError):
        client.upload_imagem(b"dados", "x.png")


def test_agendar_post_monta_payload_correto() -> None:
    capturado: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/posts")
        capturado["body"] = json.loads(request.content)
        return httpx.Response(200, json={"id": "post-42"})

    client = _client(handler)
    ag = PostizAgendamento(
        canal_id="canal-1",
        conteudo="legenda",
        data_utc="2026-05-25T12:00:00.000Z",
        plataforma="instagram",
        midias=[PostizMidia(id="img-9", path="/up/x.png")],
    )
    resultado = client.agendar_post(ag)
    assert resultado.post_url == "post-42"

    body = capturado["body"]
    assert isinstance(body, dict)
    assert body["type"] == "schedule"
    assert body["date"] == "2026-05-25T12:00:00.000Z"
    post = body["posts"][0]
    assert post["integration"]["id"] == "canal-1"
    assert post["value"][0]["content"] == "legenda"
    assert post["value"][0]["image"] == [{"id": "img-9", "path": "/up/x.png"}]
    assert post["settings"]["__type"] == "instagram"
    assert post["settings"]["post_type"] == "post"


def test_agendar_post_story_envia_post_type_story() -> None:
    capturado: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        capturado["body"] = json.loads(request.content)
        return httpx.Response(200, json={"id": "story-1"})

    client = _client(handler)
    ag = PostizAgendamento(
        canal_id="canal-1",
        conteudo="legenda",
        data_utc="2026-05-25T12:00:00.000Z",
        plataforma="instagram",
        post_type="story",
    )
    client.agendar_post(ag)

    body = capturado["body"]
    assert isinstance(body, dict)
    assert body["posts"][0]["settings"]["post_type"] == "story"


def test_agendar_post_http_erro_levanta_postiz_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="nao autorizado")

    client = _client(handler)
    ag = PostizAgendamento(canal_id="c", conteudo="x", data_utc="2026-05-25T12:00:00.000Z")
    with pytest.raises(PostizError):
        client.agendar_post(ag)


def test_construtor_token_vazio_levanta() -> None:
    with pytest.raises(PostizError):
        HttpPostizClient(token="")
