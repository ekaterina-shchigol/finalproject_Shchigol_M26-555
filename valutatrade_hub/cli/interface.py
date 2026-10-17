import shlex

from valutatrade_hub.cli.rates_commands import show_rates
from valutatrade_hub.core.currencies import CURRENCY_REGISTRY
from valutatrade_hub.core.exceptions import ApiRequestError, CurrencyNotFoundError
from valutatrade_hub.core.usecases import (
    buy,
    get_portfolio_values,
    get_rate,
    login,
    register,
    sell,
)
from valutatrade_hub.logging_config import parser_console_logging
from valutatrade_hub.parser_service.api_clients import (
    CoinGeckoClient,
    ExchangeRateApiClient,
)
from valutatrade_hub.parser_service.config import ParserConfig
from valutatrade_hub.parser_service.storage import RatesStorage
from valutatrade_hub.parser_service.updater import RatesUpdater


def _parse_options(arguments: list[str]) -> dict[str, str]:
    """Разобрать пары вида --имя значение."""
    if len(arguments) % 2 != 0:
        raise ValueError("После каждого параметра должно быть значение")

    options = {}
    for name, value in zip(arguments[::2], arguments[1::2], strict=True):
        if not name.startswith("--") or name in options:
            raise ValueError(f"Некорректный или повторный параметр: {name}")
        options[name] = value

    return options


def run_cli() -> None:
    """Запустить консольный интерфейс."""
    print("ValutaTrade Hub. Для выхода введите exit.")

    current_user = None

    while True:
        try:
            line = input("ValutaTrade> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nДо свидания!")
            break

        if not line:
            continue

        try:
            parts = shlex.split(line)
        except ValueError as error:
            print(f"Не удалось разобрать команду: {error}")
            continue

        command = parts[0].lower()
        if command == "exit":
            print("До свидания!")
            break

        if command == "update-rates":
            try:
                options = _parse_options(parts[1:])
                if set(options) - {"--source"}:
                    raise ValueError(
                        "Используйте: update-rates "
                        "[--source coingecko|exchangerate]"
                    )

                source = options.get("--source")
                if source is not None:
                    source = source.strip().lower()

                config = ParserConfig()
                clients = {
                    "coingecko": CoinGeckoClient(config),
                    "exchangerate": ExchangeRateApiClient(config),
                }
                updater = RatesUpdater(clients, RatesStorage())

                with parser_console_logging():
                    result = updater.run_update(source)
            except ApiRequestError as error:
                print(f"Ошибка: {error}")
                print("Повторите позже или проверьте сеть и API-ключ.")
            except ValueError as error:
                print(f"Ошибка: {error}")
            else:
                print(
                    f"Обновление завершено. Получено курсов: "
                    f"{result['fetched']}; обновлено в кэше: "
                    f"{result['updated']}."
                )
                print(f"Время обновления: {result['last_refresh']}")
                if result["errors"]:
                    print("Некоторые источники не ответили:")
                    for name, message in result["errors"].items():
                        print(f"- {name}: {message}")
                    print("Подробности: logs/parser.log")
            continue

        if command == "show-rates":
            try:
                options = _parse_options(parts[1:])
                show_rates(options)
            except CurrencyNotFoundError as error:
                print(f"Ошибка: {error}")
                print(f"Доступные валюты: {', '.join(CURRENCY_REGISTRY)}")
            except ApiRequestError as error:
                print(f"Ошибка: {error}")
            except (TypeError, ValueError) as error:
                print(f"Ошибка: {error}")
            continue

        if command == "register":
            try:
                options = _parse_options(parts[1:])
                if set(options) != {"--username", "--password"}:
                    raise ValueError(
                        "Используйте: register --username ИМЯ --password ПАРОЛЬ"
                    )
                user = register(options["--username"], options["--password"])
            except (TypeError, ValueError) as error:
                print(f"Ошибка: {error}")
            else:
                print(
                    f"Пользователь '{user.username}' зарегистрирован "
                    f"(id={user.user_id})."
                )
            continue

        if command == "login":
            try:
                options = _parse_options(parts[1:])
                if set(options) != {"--username", "--password"}:
                    raise ValueError(
                        "Используйте: login --username ИМЯ --password ПАРОЛЬ"
                    )
                current_user = login(options["--username"], options["--password"])
            except (TypeError, ValueError) as error:
                print(f"Ошибка: {error}")
            else:
                print(f"Вы вошли как '{current_user.username}'")
            continue

        if command == "show-portfolio":
            if current_user is None:
                print("Сначала выполните login")
                continue

            try:
                options = _parse_options(parts[1:])
                if set(options) - {"--base"}:
                    raise ValueError("Используйте: show-portfolio [--base ВАЛЮТА]")

                base = options.get("--base", "USD").strip().upper()
                rows, total = get_portfolio_values(current_user, base)
            except ApiRequestError as error:
                print(f"Ошибка: {error}")
                print("Попробуйте обновить курсы позже или проверьте сеть")
            except (TypeError, ValueError) as error:
                print(f"Ошибка: {error}")
            else:
                print(f"Портфель пользователя '{current_user.username}' (база: {base}):")
                if not rows:
                    print("В портфеле пока нет кошельков")
                else:
                    for code, balance, value in rows:
                        print(f"- {code}: {balance:.4f} → {value:.2f} {base}")
                print(f"ИТОГО: {total:.2f} {base}")
            continue

        if command == "buy":
            if current_user is None:
                print("Сначала выполните login")
                continue

            try:
                options = _parse_options(parts[1:])
                if set(options) != {"--currency", "--amount"}:
                    raise ValueError(
                        "Используйте: buy --currency ВАЛЮТА --amount КОЛИЧЕСТВО"
                    )

                amount = float(options["--amount"])
                before, after, estimated = buy(
                    current_user, options["--currency"], amount
                )
            except CurrencyNotFoundError as error:
                print(f"Ошибка: {error}")
                print(f"Доступные валюты: {', '.join(CURRENCY_REGISTRY)}")
            except ApiRequestError as error:
                print(f"Ошибка: {error}")
                print("Попробуйте обновить курсы позже или проверьте сеть")
            except (TypeError, ValueError) as error:
                print(f"Ошибка: {error}")
            else:
                code = options["--currency"].strip().upper()
                print(f"Покупка выполнена: {amount:.4f} {code}")
                print(f"- {code}: было {before:.4f} → стало {after:.4f}")
                print(f"Оценочная стоимость: {estimated:.2f} USD")
            continue

        if command == "sell":
            if current_user is None:
                print("Сначала выполните login")
                continue

            try:
                options = _parse_options(parts[1:])
                if set(options) != {"--currency", "--amount"}:
                    raise ValueError(
                        "Используйте: sell --currency ВАЛЮТА --amount КОЛИЧЕСТВО"
                    )

                amount = float(options["--amount"])
                before, after, estimated = sell(
                    current_user, options["--currency"], amount
                )
            except CurrencyNotFoundError as error:
                print(f"Ошибка: {error}")
                print(f"Доступные валюты: {', '.join(CURRENCY_REGISTRY)}")
            except ApiRequestError as error:
                print(f"Ошибка: {error}")
                print("Попробуйте обновить курсы позже или проверьте сеть")
            except (TypeError, ValueError) as error:
                print(f"Ошибка: {error}")
            else:
                code = options["--currency"].strip().upper()
                print(f"Продажа выполнена: {amount:.4f} {code}")
                print(f"- {code}: было {before:.4f} → стало {after:.4f}")
                print(f"Оценочная выручка: {estimated:.2f} USD")
            continue

        if command == "get-rate":
            try:
                options = _parse_options(parts[1:])
                if set(options) != {"--from", "--to"}:
                    raise ValueError(
                        "Используйте: get-rate --from ВАЛЮТА --to ВАЛЮТА"
                    )

                source = options["--from"].strip().upper()
                target = options["--to"].strip().upper()
                rate, reverse_rate, updated_at = get_rate(source, target)
            except CurrencyNotFoundError as error:
                print(f"Ошибка: {error}")
                print(f"Доступные валюты: {', '.join(CURRENCY_REGISTRY)}")
            except ApiRequestError as error:
                print(f"Ошибка: {error}")
                print("Попробуйте обновить курсы позже или проверьте сеть")
            except (TypeError, ValueError) as error:
                print(f"Ошибка: {error}")
            else:
                print(f"Курс {source} → {target}: {rate:.8f}")
                print(f"Обратный курс {target} → {source}: {reverse_rate:.8f}")
                if updated_at is not None:
                    print(f"Обновлено: {updated_at}")
            continue

        print(f"Неизвестная команда: {command}")