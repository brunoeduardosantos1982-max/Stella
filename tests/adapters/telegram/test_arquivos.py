from stella.adapters.telegram.arquivos import enviar_documento, enviar_foto


class _Resp:
    def raise_for_status(self):
        pass


def test_enviar_documento_chama_send_document(tmp_path):
    f = tmp_path / "a.pdf"
    f.write_bytes(b"%PDF")
    chamadas = []

    def fake_post(url, **kw):
        chamadas.append((url, kw))
        return _Resp()

    enviar_documento("TOK", "42", f, legenda="oi", http_post=fake_post)
    url, kw = chamadas[0]
    assert url.endswith("/sendDocument")
    assert kw["data"] == {"chat_id": "42", "caption": "oi"}
    assert "document" in kw["files"]


def test_enviar_foto_chama_send_photo(tmp_path):
    f = tmp_path / "s.png"
    f.write_bytes(b"x")
    chamadas = []

    def fake_post(url, **kw):
        chamadas.append(url)
        return _Resp()

    enviar_foto("TOK", "42", f, http_post=fake_post)
    assert chamadas[0].endswith("/sendPhoto")
