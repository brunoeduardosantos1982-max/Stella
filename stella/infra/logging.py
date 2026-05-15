import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def setup_logging(log_dir: Path | None = None) -> logging.Logger:
    """Configura o logger 'stella' com saída rotativa em arquivo.

    Idempotente: chamar mais de uma vez não duplica handlers.
    """
    if log_dir is None:
        log_dir = Path.home() / ".stella" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("stella")
    logger.setLevel(logging.INFO)

    if logger.handlers:
        return logger

    log_file = log_dir / "stella.log"
    handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=7,
        encoding="utf-8",
    )
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger
