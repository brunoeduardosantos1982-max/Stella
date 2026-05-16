from stella.domain.enums import ModeloIA


def test_modelo_ia_tem_tres_valores() -> None:
    assert ModeloIA.GEMMA.value == "gemma"
    assert ModeloIA.SONNET.value == "sonnet"
    assert ModeloIA.OPUS.value == "opus"


def test_modelo_ia_e_str_enum() -> None:
    assert ModeloIA.GEMMA == "gemma"  # str-Enum compara direto com string
