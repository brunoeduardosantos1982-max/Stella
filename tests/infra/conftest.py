import logging

import pytest


@pytest.fixture(autouse=True)
def reset_stella_logger():
    """Remove handlers do logger 'stella' entre testes para evitar poluição de estado."""
    yield
    logger = logging.getLogger("stella")
    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)
