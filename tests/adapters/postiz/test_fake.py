import pytest

from stella.adapters.postiz.base import PostizAgendamento, PostizError


def test_fake_postiz_upload_registra_e_devolve_midia() -> None:
    from stella.adapters.postiz.fake import FakePostiz

    fake = FakePostiz()
    midia = fake.upload_imagem(b"bytes-img", "foto.png")
    assert midia.id == "fake-img-1"
    assert fake.uploads == [("foto.png", b"bytes-img")]


def test_fake_postiz_agendar_registra_e_devolve_url() -> None:
    from stella.adapters.postiz.fake import FakePostiz

    fake = FakePostiz()
    ag = PostizAgendamento(canal_id="c1", conteudo="oi", data_utc="2026-05-25T12:00:00.000Z")
    resultado = fake.agendar_post(ag)
    assert resultado.post_url == "https://postiz.fake/post/1"
    assert fake.agendamentos == [ag]


def test_fake_postiz_falhar_em_upload() -> None:
    from stella.adapters.postiz.fake import FakePostiz

    fake = FakePostiz(falhar_em="upload")
    with pytest.raises(PostizError):
        fake.upload_imagem(b"x", "foto.png")


def test_fake_postiz_falhar_em_agendar() -> None:
    from stella.adapters.postiz.fake import FakePostiz

    ag = PostizAgendamento(canal_id="c1", conteudo="oi", data_utc="2026-05-25T12:00:00.000Z")
    fake = FakePostiz(falhar_em="agendar")
    with pytest.raises(PostizError):
        fake.agendar_post(ag)


def test_fake_postiz_satisfaz_protocolo() -> None:
    from stella.adapters.postiz.base import PostizClientProtocol
    from stella.adapters.postiz.fake import FakePostiz

    def aceita_client(c: PostizClientProtocol) -> None:
        pass

    aceita_client(FakePostiz())
