from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.logging_config import configure_parser_logging
from valutatrade_hub.parser_service.api_clients import BaseApiClient
from valutatrade_hub.parser_service.storage import RatesStorage


class RatesUpdater:
    """Опросить источники и сохранить полученные курсы."""

    def __init__(
        self,
        clients: dict[str, BaseApiClient],
        storage: RatesStorage,
    ) -> None:
        self.clients = clients
        self.storage = storage
        self.logger = configure_parser_logging()

    def run_update(self, source: str | None = None) -> dict:
        """Обновить курсы одного источника или всех доступных."""
        if source is not None and source not in self.clients:
            raise ValueError(f"Неизвестный источник курсов: {source}")

        selected = (
            {source: self.clients[source]}
            if source is not None
            else self.clients
        )
        self.logger.info("Начато обновление курсов")
        combined_rates = {}
        errors = {}

        for name, client in selected.items():
            self.logger.info("Запрос курсов: %s", name)
            try:
                rates = client.fetch_rates()
            except ApiRequestError as error:
                errors[name] = str(error)
                self.logger.error("Источник %s: %s", name, error)
                continue

            combined_rates.update(rates)
            self.logger.info(
                "Источник %s: получено %s курсов",
                name,
                len(rates),
            )

        if not combined_rates:
            self.logger.error("Обновление не удалось: нет новых курсов")
            raise ApiRequestError(
                "ни один источник не вернул курсы; проверьте logs/parser.log"
            )

        updated_count = self.storage.save_rates(combined_rates)
        cache = self.storage.database.read_object("rates_file")
        last_refresh = cache.get("last_refresh")

        self.logger.info(
            "Обновление завершено: получено %s, обновлено %s, ошибок %s",
            len(combined_rates),
            updated_count,
            len(errors),
        )
        return {
            "fetched": len(combined_rates),
            "updated": updated_count,
            "last_refresh": last_refresh,
            "errors": errors,
        }