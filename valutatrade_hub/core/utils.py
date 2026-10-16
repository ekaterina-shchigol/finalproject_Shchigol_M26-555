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