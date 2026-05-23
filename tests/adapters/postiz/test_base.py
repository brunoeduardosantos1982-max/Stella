import pytest


def test_postiz_midia_dataclass() -> None:
    from stella.adapters.postiz.base import PostizMidia

    m = PostizMidia(id="img-1", path="/uploads/x.png")
    assert m.id == "img-1"
    assert m.path == "/uploads/x.png"


def test_postiz_agendamento_defaults() -> None:
    from stella.adapters.postiz.base import PostizAgendamento

    ag = PostizAgendamento(canal_id="c1", conteudo="oi", data_utc="2026-05-25T12:00:00.000Z")
    assert ag.plataforma == "instagram"
    assert ag.midias == []


def test_postiz_resultado_default() -> None:
    from stella.adapters.postiz.base import PostizResultado

    r = PostizResultado()
    assert r.post_url is None


def test_postiz_error_e_excecao() -> None:
    from stella.adapters.postiz.base import PostizError

    assert issubclass(PostizError, Exception)
    with pytest.raises(PostizError):
        raise PostizError("falha")
