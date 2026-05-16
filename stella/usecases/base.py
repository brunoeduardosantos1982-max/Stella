class UsecaseError(Exception):
    """Erro genérico de usecase (fronteira da camada de aplicação)."""


class EntradaInvalida(UsecaseError):
    """A entrada fornecida ao usecase não é válida."""
