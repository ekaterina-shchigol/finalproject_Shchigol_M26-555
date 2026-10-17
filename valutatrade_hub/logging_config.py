import logging
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from logging.handlers import RotatingFileHandler
from pathlib import Path

from valutatrade_hub.infra.settings import SettingsLoader


def configure_logging(debug: bool = False) -> logging.Logger:
    """Настроить текстовый журнал операций с ротацией файлов."""
    settings = SettingsLoader()
    if settings.get("log_format") != "text":
        raise ValueError("Поддерживается только текстовый формат журнала")

    log_path = Path(__file__).resolve().parents[1] / settings.get("log_path")
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("valutatrade.actions")
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    logger.propagate = False

    if not logger.handlers:
        handler = RotatingFileHandler(
            log_path,
            maxBytes=1_000_000,
            backupCount=3,
            encoding="utf-8",
        )
        handler.setFormatter(
            logging.Formatter(
                "%(levelname)s %(asctime)s %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S%z",
            )
        )
        logger.addHandler(handler)

    return logger


def configure_parser_logging(debug: bool = False) -> logging.Logger:
    """Настроить файловый журнал Parser Service с ротацией."""
    log_path = Path(__file__).resolve().parents[1] / "logs/parser.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("valutatrade.parser")
    logger.setLevel(logging.DEBUG if debug else logging.INFO)
    logger.propagate = False

    if not logger.handlers:
        handler = RotatingFileHandler(
            log_path,
            maxBytes=1_000_000,
            backupCount=3,
            encoding="utf-8",
        )
        handler.setFormatter(
            logging.Formatter(
                "%(levelname)s %(asctime)s %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S%z",
            )
        )
        logger.addHandler(handler)

    return logger


@contextmanager
def parser_console_logging() -> Iterator[None]:
    """Показывать логи парсера в консоли только внутри команды update-rates."""
    logger = configure_parser_logging()
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logger.addHandler(handler)

    try:
        yield
    finally:
        logger.removeHandler(handler)
        handler.close()