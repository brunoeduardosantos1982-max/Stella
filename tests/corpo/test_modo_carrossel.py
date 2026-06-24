"""Testes do roteamento de modo carrossel no daemon (F3).

A decisão de modo é uma função pura (texto + modo sticky -> 'carrossel'|'reel'|None)
e o modo é persistido no estado sticky para os follow-ups herdarem a persona certa.
"""

from stella.corpo import daemon_telegram as d


def test_escolher_modo_carrossel():
    assert d._escolher_modo("faz um carrossel sobre agentes", None) == "carrossel"


def test_escolher_modo_reel():
    assert d._escolher_modo("cria um script de reels sobre marketing", None) == "reel"


def test_carrossel_tem_prioridade_sobre_conteudo_generico():
    # "conteúdo" casaria o gatilho reel, mas "carrossel" vence.
    assert d._escolher_modo("faz um carrossel de conteúdo", None) == "carrossel"


def test_followup_herda_modo_sticky():
    assert d._escolher_modo("e qual o gancho?", "carrossel") == "carrossel"
    assert d._escolher_modo("melhora o slide 2", "reel") == "reel"


def test_chat_normal_nao_tem_modo():
    assert d._escolher_modo("bom dia, tudo certo?", None) is None


def test_ativar_e_ler_modo_sticky(tmp_path, monkeypatch):
    state = tmp_path / "conteudo.json"
    monkeypatch.setattr(d, "CONTEUDO_STATE", state)
    d._ativar_conteudo("carrossel")
    assert d._modo_sticky() == "carrossel"
    assert d._conteudo_ativo() is True
