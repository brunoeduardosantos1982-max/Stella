"""Testes da persona do modo carrossel (F1).

A persona é o prompt-contrato injetado no cérebro (claude -p). Estes testes
travam os invariantes que não podem se perder em edições futuras: sem travessão,
cita os comandos da fábrica, exige aprovação e keyword, e o gatilho detecta.
"""

from stella.corpo.persona_carrossel import GATILHO_CARROSSEL, PERSONA_CARROSSEL


def test_persona_sem_travessao():
    # em-dash é digital de IA; proibido em copy pública e no próprio prompt.
    assert "—" not in PERSONA_CARROSSEL


def test_persona_cita_os_comandos_da_fabrica():
    for cmd in (
        "stella carrossel",
        "stella material",
        "stella manychat",
        "stella publicar-material",
    ):
        assert cmd in PERSONA_CARROSSEL


def test_persona_exige_aprovacao_e_keyword():
    baixa = PERSONA_CARROSSEL.lower()
    assert "aprov" in baixa
    assert "keyword" in baixa


def test_persona_cita_os_tres_segmentos():
    baixa = PERSONA_CARROSSEL.lower()
    assert "autoridade" in baixa
    assert "build-in-public" in baixa or "build in public" in baixa
    assert "ensino" in baixa


def test_gatilho_detecta_carrossel_e_ignora_conversa():
    assert GATILHO_CARROSSEL.search("Stella, faz um carrossel sobre agentes")
    assert GATILHO_CARROSSEL.search("cria um carrossel disso pra mim")
    assert GATILHO_CARROSSEL.search("monta um CARROSSEL desse drop")
    assert GATILHO_CARROSSEL.search("faz um carousel sobre isso")
    assert not GATILHO_CARROSSEL.search("bom dia, tudo certo?")
