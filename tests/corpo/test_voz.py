from stella.corpo import voz


def test_limpar_para_fala_remove_emoji_markdown_url_e_codigo() -> None:
    texto = (
        "🎤 **Site no ar!**\n\n"
        "Veja em https://josiedealbuquerque.com.br e o código `npm run build` rodou.\n"
        "```python\nprint('oi')\n```\n"
        "Tudo certo ⚡"
    )

    limpo = voz.limpar_para_fala(texto)

    assert "🎤" not in limpo
    assert "⚡" not in limpo
    assert "**" not in limpo
    assert "https://" not in limpo
    assert "npm run build" not in limpo
    assert "print" not in limpo
    assert "Site no ar!" in limpo
    assert "Tudo certo" in limpo


def test_encurtar_para_fala_corta_em_frase_e_avisa() -> None:
    texto = ("Primeira frase completa. " * 100).strip()

    curto = voz.encurtar_para_fala(texto, limite=200)

    assert len(curto) < 300
    assert curto.startswith("Primeira frase completa.")
    assert curto.endswith("posso detalhar o resto se quiser.")


def test_encurtar_para_fala_nao_mexe_em_texto_curto() -> None:
    assert voz.encurtar_para_fala("Oi Bruno.", limite=200) == "Oi Bruno."
