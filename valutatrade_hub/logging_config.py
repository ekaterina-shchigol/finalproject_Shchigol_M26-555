import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from valutatrade_hub.infra.settings import SettingsLoader


def configure_logging(debug: bool = False) -> logging.Logger:
    """Настроить журнал операций с ротацией файлов."""
    settings = SettingsLoader()
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