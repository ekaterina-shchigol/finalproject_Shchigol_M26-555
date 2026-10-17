from math import isfinite

from valutatrade_hub.core.currencies import (
    CURRENCY_REGISTRY,
    CryptoCurrency,
    get_currency,
)
from valutatrade_hub.core.utils import is_rate_fresh
from valutatrade_hub.infra.database import DatabaseManager


def list_cached_rates(
    currency: str | None = None,
    top: int | None = None,
    base: str = "USD",
) -> tuple[list[tuple[str, float, str]], str | None]:
    """Вернуть курсы из локального кэша с фильтрацией и сортировкой."""
    if top is not None and top <= 0:
        raise ValueError("--top должен быть положительным числом")

    base_code = get_currency(base).code
    currency_code = currency.strip().upper() if currency else None

    cache = DatabaseManager().read_object("rates_file")
    pairs = cache.get("pairs")
    if not isinstance(pairs, dict) or not pairs:
        raise ValueError(
            "Локальный кэш курсов пуст. Выполните update-rates"
        )

    base_rate = 1.0
    if base_code != "USD":
        base_entry = pairs.get(f"{base_code}_USD")
        if not isinstance(base_entry, dict):
            raise ValueError(
                f"Курс для базы '{base_code}' не найден в кэше"
            )

        base_rate = base_entry.get("rate")
        base_updated_at = base_entry.get("updated_at")
        if (
            isinstance(base_rate, bool)
            or not isinstance(base_rate, (int, float))
            or not isfinite(base_rate)
            or base_rate <= 0
            or not isinstance(base_updated_at, str)
        ):
            raise ValueError(
                f"Неверный курс для базы '{base_code}'"
            )

        try:
            base_is_fresh = is_rate_fresh(base_updated_at)
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"Неверная дата курса для базы '{base_code}'"
            ) from error
        if not base_is_fresh:
            raise ValueError(
                f"Курс для базы '{base_code}' устарел. "
                "Выполните update-rates"
            )

    rows = []
    for pair, entry in pairs.items():
        if not pair.endswith("_USD") or not isinstance(entry, dict):
            continue

        code = pair.removesuffix("_USD")
        if code not in CURRENCY_REGISTRY:
            continue
        if currency_code is not None and code != currency_code:
            continue
        if top is not None and not isinstance(
            CURRENCY_REGISTRY[code], CryptoCurrency
        ):
            continue

        rate = entry.get("rate")
        updated_at = entry.get("updated_at")
        if (
            isinstance(rate, bool)
            or not isinstance(rate, (int, float))
            or not isfinite(rate)
            or rate <= 0
            or not isinstance(updated_at, str)
        ):
            raise ValueError(f"Неверный курс для '{code}'")

        try:
            fresh = is_rate_fresh(updated_at)
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"Неверная дата курса '{code}'"
            ) from error
        if not fresh:
            raise ValueError(
                f"Курс '{code}' устарел. Выполните update-rates"
            )

        rows.append((code, rate / base_rate, updated_at))

    if top is not None:
        rows.sort(key=lambda row: row[1], reverse=True)
        rows = rows[:top]
    else:
        rows.sort(key=lambda row: row[0])

    return rows, cache.get("last_refresh")