import logging

from stella.infra.logging import setup_logging


def test_setup_logging_retorna_logger_nomeado(tmp_path):
    logger = setup_logging(log_dir=tmp_path)
    assert logger.name == "stella"
    assert logger.level == logging.INFO


def test_setup_logging_cria_arquivo_de_log(tmp_path):
    logger = setup_logging(log_dir=tmp_path)
    logger.info("teste de mensagem")
    for handler in logger.handlers:
        handler.flush()
    log_file = tmp_path / "stella.log"
    assert log_file.exists()
    assert "teste de mensagem" in log_file.read_text(encoding="utf-8")


def test_setup_logging_nao_duplica_handlers(tmp_path):
    logger1 = setup_logging(log_dir=tmp_path)
    n_handlers = len(logger1.handlers)
    logger2 = setup_logging(log_dir=tmp_path)
    assert len(logger2.handlers) == n_handlers
