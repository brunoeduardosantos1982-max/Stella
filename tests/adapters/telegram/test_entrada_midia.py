"""Recebimento de mídia pelo Telegram: roteamento, nome e o caso do arquivo grande."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from stella.adapters.telegram.entrada_midia import (
    ArquivoGrandeDemais,
    apelidar,
    escolher_pasta,
    extrair_midia,
    guardar,
    montar_nome,
)

AGORA = datetime(2026, 7, 27, 14, 30, tzinfo=timezone(timedelta(hours=-3)))


class RespostaFake:
    def __init__(self, payload=None, conteudo=b"", ok=True):
        self._payload = payload or {}
        self.content = conteudo
        self._ok = ok

    def json(self):
        return self._payload

    def raise_for_status(self):
        if not self._ok:
            raise AssertionError("status ruim")


def http_fake(conteudo=b"video-binario"):
    """getFile devolve caminho; o segundo GET devolve o binário."""

    def _get(url, **_):
        if "getFile" in url:
            return RespostaFake({"ok": True, "result": {"file_path": "videos/file_1.mp4"}})
        return RespostaFake(conteudo=conteudo)

    return _get


def test_apelidar_tira_acento_e_pontuacao():
    assert apelidar("Praia de Maceió!") == "praia-de-maceio"
    assert apelidar("  ") == ""


def test_legenda_com_story_vai_para_stories():
    assert escolher_pasta("story bastidor") == "stories"
    assert escolher_pasta("STORIES da viagem") == "stories"


def test_sem_pista_cai_em_reels():
    assert escolher_pasta("bastidor do bot") == "reels"
    assert escolher_pasta("") == "reels"


def test_extrai_video():
    m = {"video": {"file_id": "abc", "file_name": "clipe.mp4", "file_size": 1234}}
    assert extrair_midia(m) == {"file_id": "abc", "nome": "clipe.mp4", "tamanho": 1234}


def test_foto_pega_o_maior_tamanho():
    m = {"photo": [{"file_id": "peq", "file_size": 10}, {"file_id": "grd", "file_size": 900}]}
    assert extrair_midia(m)["file_id"] == "grd"


def test_audio_e_voz_nao_sao_midia_de_entrada():
    # Quem cuida deles e a transcricao; se entrassem aqui, todo comando de voz
    # viraria arquivo na pasta de Reels.
    assert extrair_midia({"voice": {"file_id": "x"}}) is None
    assert extrair_midia({"audio": {"file_id": "x"}}) is None


def test_mensagem_sem_midia():
    assert extrair_midia({"text": "oi"}) is None


def test_nome_leva_data_apelido_e_extensao():
    assert montar_nome("Praia de Maceió", "clipe.mp4", AGORA) == (
        "2026-07-27-1430__praia-de-maceio.mp4"
    )


def test_nome_sem_legenda_ainda_e_valido():
    assert montar_nome("", "clipe.mov", AGORA) == "2026-07-27-1430__sem-legenda.mov"


def test_guardar_escreve_na_pasta_certa(tmp_path: Path):
    mensagem = {
        "video": {"file_id": "abc", "file_name": "clipe.mp4", "file_size": 100},
        "caption": "story bastidor do bot",
    }
    destino, pasta = guardar(mensagem, "tok", raiz=tmp_path, http_get=http_fake(), agora=AGORA)
    assert pasta == "stories"
    assert destino == tmp_path / "stories" / "2026-07-27-1430__story-bastidor-do-bot.mp4"
    assert destino.read_bytes() == b"video-binario"


def test_guardar_devolve_none_sem_midia(tmp_path: Path):
    assert guardar({"text": "oi"}, "tok", raiz=tmp_path, http_get=http_fake()) is None


# O caso que decide se o canal serve: bot do Telegram nao baixa acima de 20 MB.
def test_arquivo_grande_demais_levanta_excecao_propria(tmp_path: Path):
    def get_recusa(url, **_):
        return RespostaFake({"ok": False, "description": "Bad Request: file is too big"})

    mensagem = {"document": {"file_id": "abc", "file_name": "grande.mp4", "file_size": 90_000_000}}
    with pytest.raises(ArquivoGrandeDemais):
        guardar(mensagem, "tok", raiz=tmp_path, http_get=get_recusa)


def test_outro_erro_do_getfile_nao_vira_arquivo_grande(tmp_path: Path):
    def get_erro(url, **_):
        return RespostaFake({"ok": False, "description": "Unauthorized"})

    with pytest.raises(ValueError):
        guardar(
            {"video": {"file_id": "a", "file_name": "x.mp4"}},
            "tok",
            raiz=tmp_path,
            http_get=get_erro,
        )


def test_lamina_de_fornecedor_vai_para_ofertas():
    for legenda in [
        "oferta nova da Incomum",
        "lâmina Maceió dezembro",
        "pacote Bariloche",
        "CATIVA bloqueio aéreo",
    ]:
        assert escolher_pasta(legenda) == "ofertas", legenda


def test_oferta_ganha_de_story_na_mesma_legenda():
    # "oferta para story" é oferta: o que vira Story se decide DEPOIS de
    # conferir preço e roteiro, não na chegada do arquivo.
    assert escolher_pasta("oferta para story") == "ofertas"


def test_legenda_inteira_fica_guardada_ao_lado(tmp_path: Path):
    mensagem = {
        "document": {"file_id": "abc", "file_name": "lamina.pdf", "file_size": 100},
        "caption": "oferta comercial, embarque Navegantes, usar em anúncio",
    }
    destino, pasta = guardar(mensagem, "tok", raiz=tmp_path, http_get=http_fake(), agora=AGORA)
    assert pasta == "ofertas"
    ao_lado = destino.with_suffix(destino.suffix + ".txt")
    assert "embarque Navegantes" in ao_lado.read_text(encoding="utf-8")


def test_sem_legenda_nao_cria_arquivo_de_texto(tmp_path: Path):
    mensagem = {"video": {"file_id": "abc", "file_name": "clipe.mp4", "file_size": 10}}
    destino, _ = guardar(mensagem, "tok", raiz=tmp_path, http_get=http_fake(), agora=AGORA)
    assert not destino.with_suffix(destino.suffix + ".txt").exists()
