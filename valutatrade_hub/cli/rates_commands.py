from valutatrade_hub.core.rates_view import list_cached_rates


def show_rates(options: dict[str, str]) -> None:
    """Напечатать курсы из локального кэша."""
    if set(options) - {"--currency", "--top", "--base"}:
        raise ValueError(
            "Используйте: show-rates "
            "[--currency ВАЛЮТА] [--top ЧИСЛО] [--base ВАЛЮТА]"
        )

    currency = options.get("--currency")
    base = options.get("--base", "USD")
    top_text = options.get("--top")
    top = int(top_text) if top_text is not None else None

    rows, last_refresh = list_cached_rates(
        currency=currency,
        top=top,
        base=base,
    )

    if not rows:
        if currency is not None:
            print(f"Курс для '{currency.strip().upper()}' не найден в кэше.")
        else:
            print("Подходящих курсов в кэше нет.")
        return

    print(f"Курсы из кэша (обновлено: {last_refresh}):")
    base_code = base.strip().upper()
    for code, rate, updated_at in rows:
        print(f"- {code}_{base_code}: {rate:.8f} (курс от {updated_at})")