from datetime import UTC, datetime, timedelta
from math import isfinite

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.infra.database import DatabaseManager
from valutatrade_hub.infra.settings import SettingsLoader

DEMO_USD_RATES = {
    "USD": 1.0,
    "EUR": 1.07,
    "BTC": 59300.0,
    "RUB": 0.01016,
    "ETH": 3720.0,
}


def normalize_currency_code(currency_code: str) -> str:
    """Проверить и привести код валюты к верхнему регистру."""
    if not isinstance(currency_code, str) or not currency_code.strip():
        raise ValueError("Код валюты не может быть пустым")

    return currency_code.strip().upper()


def get_demo_rate(from_currency: str, to_currency: str) -> float:
    """Вернуть учебный курс исходной валюты к целевой."""
    source = normalize_currency_code(from_currency)
    target = normalize_currency_code(to_currency)

    if source not in DEMO_USD_RATES:
        raise ValueError(f"Нет учебного курса для '{source}'")
    if target not in DEMO_USD_RATES:
        raise ValueError(f"Нет учебного курса для '{target}'")

    return DEMO_USD_RATES[source] / DEMO_USD_RATES[target]


def is_rate_fresh(updated_at: str) -> bool:
    """Проверить срок актуальности курса из локального кэша."""
    updated = datetime.fromisoformat(updated_at)
    ttl_seconds = SettingsLoader().get("rates_ttl_seconds")
    return datetime.now(UTC) - updated <= timedelta(seconds=ttl_seconds)


def get_cached_usd_rate(currency_code: str) -> float | None:
    """Вернуть свежий курс валюты к USD или None, если кэша ещё нет."""
    code = normalize_currency_code(currency_code)
    if code == "USD":
        return 1.0

    cache = DatabaseManager().read_object("rates_file")
    if not cache:
        return None

    pairs = cache.get("pairs")
    if not isinstance(pairs, dict):
        raise ApiRequestError("Неверный формат локального кэша курсов")

    entry = pairs.get(f"{code}_USD")
    if not isinstance(entry, dict):
        raise ApiRequestError(f"Курс {code} → USD отсутствует в локальном кэше")

    rate = entry.get("rate")
    updated_at = entry.get("updated_at")
    if (
        isinstance(rate, bool)
        or not isinstance(rate, (int, float))
        or not isfinite(rate)
        or rate <= 0
        or not isinstance(updated_at, str)
    ):
        raise ApiRequestError(f"Неверные данные курса {code} → USD")

    try:
        fresh = is_rate_fresh(updated_at)
    except (TypeError, ValueError) as error:
        raise ApiRequestError(f"Неверная дата курса {code} → USD") from error

    if not fresh:
        raise ApiRequestError(
            f"Курс {code} → USD устарел. Выполните update-rates"
        )

    return float(rate)


def get_current_rate(from_currency: str, to_currency: str) -> float:
    """Вернуть курс из кэша либо учебный курс, пока кэш пуст."""
    source = normalize_currency_code(from_currency)
    target = normalize_currency_code(to_currency)

    cache = DatabaseManager().read_object("rates_file")
    if not cache:
        return get_demo_rate(source, target)

    source_usd = get_cached_usd_rate(source)
    target_usd = get_cached_usd_rate(target)
    if source_usd is None or target_usd is None:
        raise ApiRequestError("Локальный кэш курсов недоступен")

    return source_usd / target_usd