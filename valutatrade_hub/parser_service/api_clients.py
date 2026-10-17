from abc import ABC, abstractmethod
from datetime import UTC, datetime
from math import isfinite

import requests

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.config import ParserConfig


class BaseApiClient(ABC):
    """Общий интерфейс источника курсов валют."""

    @abstractmethod
    def fetch_rates(self) -> dict[str, dict]:
        """Вернуть курсы в едином формате по ключам вида BTC_USD."""


class CoinGeckoClient(BaseApiClient):
    """Получить курсы криптовалют из CoinGecko."""

    def __init__(self, config: ParserConfig) -> None:
        self.config = config

    def fetch_rates(self) -> dict[str, dict]:
        """Получить курсы криптовалют к базовой валюте."""
        coin_ids = [
            self.config.crypto_id_map[code] for code in self.config.crypto_currencies
        ]
        params = {
            "ids": ",".join(coin_ids),
            "vs_currencies": self.config.base_currency.lower(),
            "include_last_updated_at": "true",
        }
        headers = {}
        if self.config.coingecko_api_key:
            headers["x-cg-demo-api-key"] = self.config.coingecko_api_key

        try:
            response = requests.get(
                self.config.coingecko_url,
                params=params,
                headers=headers,
                timeout=self.config.request_timeout,
            )
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as error:
            raise ApiRequestError(
                f"CoinGecko: ошибка сети или HTTP ({type(error).__name__})"
            ) from error
        except ValueError as error:
            raise ApiRequestError(
                "CoinGecko: ответ не является корректным JSON"
            ) from error

        if not isinstance(data, dict):
            raise ApiRequestError("CoinGecko: неверный формат ответа")

        rates = {}
        base = self.config.base_currency.upper()
        fetched_at = datetime.now(UTC).isoformat()

        for code in self.config.crypto_currencies:
            coin_id = self.config.crypto_id_map[code]
            coin_data = data.get(coin_id)
            if not isinstance(coin_data, dict):
                raise ApiRequestError(f"CoinGecko: нет данных для {code}")

            rate = coin_data.get(base.lower())
            if (
                isinstance(rate, bool)
                or not isinstance(rate, (int, float))
                or not isfinite(rate)
                or rate <= 0
            ):
                raise ApiRequestError(f"CoinGecko: неверный курс для {code}")

            source_updated_unix = coin_data.get("last_updated_at")
            source_updated_at = None
            if (
                not isinstance(source_updated_unix, bool)
                and isinstance(source_updated_unix, (int, float))
                and source_updated_unix > 0
            ):
                source_updated_at = datetime.fromtimestamp(
                    source_updated_unix, UTC
                ).isoformat()

            rates[f"{code}_{base}"] = {
                "rate": float(rate),
                "updated_at": fetched_at,
                "source": "CoinGecko",
                "meta": {
                    "raw_id": coin_id,
                    "source_updated_at": source_updated_at,
                },
            }

        return rates


class ExchangeRateApiClient(BaseApiClient):
    """Получить курсы фиатных валют из ExchangeRate-API."""

    def __init__(self, config: ParserConfig) -> None:
        self.config = config

    def fetch_rates(self) -> dict[str, dict]:
        """Получить курсы фиатных валют к базовой валюте."""
        api_key = self.config.exchangerate_api_key
        if not api_key:
            raise ApiRequestError("ExchangeRate-API: не задан EXCHANGERATE_API_KEY")

        base = self.config.base_currency.upper()
        url = f"{self.config.exchangerate_api_url}/{api_key}/latest/{base}"

        try:
            response = requests.get(
                url,
                timeout=self.config.request_timeout,
            )
            if response.status_code == 429:
                raise ApiRequestError("ExchangeRate-API: превышен лимит запросов")
            if response.status_code in (401, 403):
                raise ApiRequestError("ExchangeRate-API: проверьте API-ключ")
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.RequestException as error:
            # В URL находится ключ, поэтому текст сетевой ошибки не показываем.
            raise ApiRequestError(
                f"ExchangeRate-API: ошибка сети или HTTP ({type(error).__name__})"
            ) from error
        except ValueError as error:
            raise ApiRequestError(
                "ExchangeRate-API: ответ не является корректным JSON"
            ) from error

        if not isinstance(data, dict) or data.get("result") != "success":
            raise ApiRequestError("ExchangeRate-API: сервис не вернул успешный ответ")
        if data.get("base_code") != base:
            raise ApiRequestError("ExchangeRate-API: неверная базовая валюта в ответе")

        conversion_rates = data.get("conversion_rates")
        if not isinstance(conversion_rates, dict):
            raise ApiRequestError("ExchangeRate-API: в ответе нет словаря курсов")

        fetched_at = datetime.now(UTC).isoformat()
        source_updated_unix = data.get("time_last_update_unix")
        source_updated_at = None
        if (
            not isinstance(source_updated_unix, bool)
            and isinstance(source_updated_unix, (int, float))
            and source_updated_unix > 0
        ):
            source_updated_at = datetime.fromtimestamp(
                source_updated_unix, UTC
            ).isoformat()

        rates = {}
        for code in self.config.fiat_currencies:
            direct_rate = conversion_rates.get(code)
            if (
                isinstance(direct_rate, bool)
                or not isinstance(direct_rate, (int, float))
                or not isfinite(direct_rate)
                or direct_rate <= 0
            ):
                raise ApiRequestError(f"ExchangeRate-API: неверный курс для {code}")

            # Ответ latest/USD содержит USD → EUR; нам нужен EUR → USD.
            rates[f"{code}_{base}"] = {
                "rate": 1 / direct_rate,
                "updated_at": fetched_at,
                "source": "ExchangeRate-API",
                "meta": {"source_updated_at": source_updated_at},
            }

        return rates
