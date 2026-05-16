import pytest

from stella.usecases.base import EntradaInvalida, UsecaseError


def test_entrada_invalida_e_subclasse_de_usecase_error() -> None:
    assert issubclass(EntradaInvalida, UsecaseError)


def test_usecase_error_e_excecao() -> None:
    assert issubclass(UsecaseError, Exception)


def test_entrada_invalida_pode_ser_levantada_com_mensagem() -> None:
    with pytest.raises(EntradaInvalida, match="campo X"):
        raise EntradaInvalida("campo X é obrigatório")
