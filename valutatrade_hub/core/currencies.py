from abc import ABC, abstractmethod
from math import isfinite

from valutatrade_hub.core.exceptions import CurrencyNotFoundError
from valutatrade_hub.core.utils import normalize_currency_code


class Currency(ABC):
    """Общие требования к фиатной или криптовалюте."""

    def __init__(self, name: str, code: str) -> None:
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Название валюты не может быть пустым")
        if not isinstance(code, str):
            raise TypeError("Код валюты должен быть строкой")

        normalized_code = code.strip().upper()
        if (
            not 2 <= len(normalized_code) <= 5
            or not normalized_code.isascii()
            or not normalized_code.isalnum()
        ):
            raise ValueError(
                "Код валюты должен содержать 2–5 латинских букв или цифр"
            )

        self.name = name.strip()
        self.code = normalized_code

    @abstractmethod
    def get_display_info(self) -> str:
        """Вернуть описание валюты для интерфейса."""


class FiatCurrency(Currency):
    """Фиатная валюта со страной или зоной эмиссии."""

    def __init__(self, name: str, code: str, issuing_country: str) -> None:
        super().__init__(name, code)
        if not isinstance(issuing_country, str) or not issuing_country.strip():
            raise ValueError("Страна или зона эмиссии не может быть пустой")

        self.issuing_country = issuing_country.strip()

    def get_display_info(self) -> str:
        """Вернуть описание фиатной валюты."""
        return (
            f"[FIAT] {self.code} — {self.name} "
            f"(Issuing: {self.issuing_country})"
        )


class CryptoCurrency(Currency):
    """Криптовалюта с алгоритмом и последней известной капитализацией."""

    def __init__(
        self,
        name: str,
        code: str,
        algorithm: str,
        market_cap: float,
    ) -> None:
        super().__init__(name, code)
        if not isinstance(algorithm, str) or not algorithm.strip():
            raise ValueError("Алгоритм не может быть пустым")
        if (
            isinstance(market_cap, bool)
            or not isinstance(market_cap, (int, float))
            or not isfinite(market_cap)
            or market_cap < 0
        ):
            raise ValueError("Капитализация должна быть конечным неотрицательным числом")

        self.algorithm = algorithm.strip()
        self.market_cap = float(market_cap)

    def get_display_info(self) -> str:
        """Вернуть описание криптовалюты."""
        market_cap_text = f"{self.market_cap:.2e}".replace("e+", "e")
        return (
            f"[CRYPTO] {self.code} — {self.name} "
            f"(Algo: {self.algorithm}, MCAP: {market_cap_text})"
        )


CURRENCY_REGISTRY: dict[str, Currency] = {
    "USD": FiatCurrency("US Dollar", "USD", "United States"),
    "EUR": FiatCurrency("Euro", "EUR", "Eurozone"),
    "GBP": FiatCurrency("Pound Sterling", "GBP", "United Kingdom"),
    "RUB": FiatCurrency("Russian Ruble", "RUB", "Russia"),
    "BTC": CryptoCurrency("Bitcoin", "BTC", "SHA-256", 1.12e12),
    "ETH": CryptoCurrency("Ethereum", "ETH", "Proof of Stake", 4.50e11),
    "SOL": CryptoCurrency("Solana", "SOL", "Proof of Stake", 6.50e10),
}


def get_currency(code: str) -> Currency:
    """Найти валюту по коду или сообщить, что она неизвестна."""
    normalized_code = normalize_currency_code(code)
    if normalized_code not in CURRENCY_REGISTRY:
        raise CurrencyNotFoundError(normalized_code)

    return CURRENCY_REGISTRY[normalized_code]