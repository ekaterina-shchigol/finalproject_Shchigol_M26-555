import time

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.logging_config import configure_parser_logging
from valutatrade_hub.parser_service.api_clients import (
    CoinGeckoClient,
    ExchangeRateApiClient,
)
from valutatrade_hub.parser_service.config import ParserConfig
from valutatrade_hub.parser_service.storage import RatesStorage
from valutatrade_hub.parser_service.updater import RatesUpdater


def run_scheduler(interval_seconds: int = 3600) -> None:
    """Периодически обновлять курсы, пока запущен этот модуль."""
    if interval_seconds <= 0:
        raise ValueError("Интервал должен быть положительным числом")

    config = ParserConfig()
    clients = {
        "coingecko": CoinGeckoClient(config),
        "exchangerate": ExchangeRateApiClient(config),
    }
    updater = RatesUpdater(clients, RatesStorage())
    logger = configure_parser_logging()

    while True:
        try:
            updater.run_update()
        except ApiRequestError as error:
            logger.error("Плановое обновление не удалось: %s", error)

        time.sleep(interval_seconds)


if __name__ == "__main__":
    run_scheduler()