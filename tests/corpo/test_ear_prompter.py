from pathlib import Path

import pytest

from stella.corpo import ear_prompter


def test_dividir_frases() -> None:
    assert ear_prompter.dividir_frases("Oi. Tudo bem? Vamos!") == ["Oi", "Tudo bem", "Vamos"]
    assert ear_prompter.dividir_frases("") == []
    assert ear_prompter.dividir_frases("Linha um\nLinha dois") == ["Linha um", "Linha dois"]


def test_montar_pausa() -> None:
    assert ear_prompter.montar_pausa(0) == ""
    assert ear_prompter.montar_pausa(3.0) == '<break time="3s" />'
    assert ear_prompter.montar_pausa(3.5) == '<break time="3s" /> <break time="0.5s" />'


def test_montar_fala_une_com_pausa() -> None:
    fala = ear_prompter.montar_fala("Primeira frase. Segunda frase.", 3.5)
    assert "Primeira frase" in fala
    assert "Segunda frase" in fala
    assert '<break time="3s" />' in fala


def test_montar_fala_vazio_levanta() -> None:
    with pytest.raises(ValueError):
        ear_prompter.montar_fala("   ", 3.5)


def test_gerar_chama_elevenlabs(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    capturado: dict[str, str] = {}

    def fake_falar(fala: str, destino: Path) -> Path:
        capturado["fala"] = fala
        destino.write_bytes(b"ID3-fake-mp3")
        return destino

    monkeypatch.setattr(ear_prompter.voz, "falar_elevenlabs", fake_falar)
    destino = tmp_path / "ear.mp3"
    saida = ear_prompter.gerar("Uma frase. Outra frase.", destino, gap_seg=3.5)

    assert saida == destino
    assert destino.exists()
    assert '<break time="3s" />' in capturado["fala"]


def test_gerar_gap_negativo_levanta(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        ear_prompter.gerar("Uma frase.", tmp_path / "x.mp3", gap_seg=-1)


def test_limpar_para_gravacao_remove_rotulos_e_rubricas() -> None:
    bruto = (
        "Gancho: Você está usando IA errado.\n"
        "[corta para close]\n"
        "Desenvolvimento: A maioria só copia resposta.\n"
        "CTA: Comenta IA aqui embaixo.\n"
        "(música sobe)\n"
        "#ia #marketing #reels"
    )
    limpo = ear_prompter.limpar_para_gravacao(bruto)
    assert "Gancho" not in limpo
    assert "CTA" not in limpo
    assert "Desenvolvimento" not in limpo
    assert "corta para close" not in limpo
    assert "música sobe" not in limpo
    assert "#" not in limpo and "hashtag" not in limpo.lower()
    assert "Você está usando IA errado." in limpo
    assert "Comenta IA aqui embaixo." in limpo
