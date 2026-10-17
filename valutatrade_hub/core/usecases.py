import hashlib
import secrets
from datetime import UTC, datetime

from valutatrade_hub.core.currencies import get_currency
from valutatrade_hub.core.exceptions import ApiRequestError, InsufficientFundsError
from valutatrade_hub.core.models import Portfolio, User, Wallet
from valutatrade_hub.core.utils import get_current_rate
from valutatrade_hub.decorators import log_action
from valutatrade_hub.infra.database import DatabaseManager
from valutatrade_hub.infra.storage import (
    load_portfolios,
    load_users,
    save_portfolios,
    save_users,
)


def get_rate(
    from_currency: str,
    to_currency: str,
) -> tuple[float, float, str | None]:
    """Вернуть курс и при необходимости обновить устаревший кэш."""
    source = get_currency(from_currency).code
    target = get_currency(to_currency).code

    try:
        rate = get_current_rate(source, target)
    except ApiRequestError:
        from valutatrade_hub.parser_service.api_clients import (
            CoinGeckoClient,
            ExchangeRateApiClient,
        )
        from valutatrade_hub.parser_service.config import ParserConfig
        from valutatrade_hub.parser_service.storage import RatesStorage
        from valutatrade_hub.parser_service.updater import RatesUpdater

        config = ParserConfig()
        clients = {
            "coingecko": CoinGeckoClient(config),
            "exchangerate": ExchangeRateApiClient(config),
        }
        updater = RatesUpdater(clients, RatesStorage())
        updater.run_update()
        rate = get_current_rate(source, target)

    cache = DatabaseManager().read_object("rates_file")
    if not cache:
        return rate, 1 / rate, None

    pairs = cache.get("pairs", {})
    timestamps = [
        pairs[f"{code}_USD"]["updated_at"] for code in (source, target) if code != "USD"
    ]
    updated_at = min(timestamps) if timestamps else cache.get("last_refresh")
    return rate, 1 / rate, updated_at


def register(username: str, password: str) -> User:
    """Зарегистрировать пользователя и создать ему пустой портфель."""
    if not isinstance(username, str) or not username.strip():
        raise ValueError("Имя пользователя не может быть пустым")
    if not isinstance(password, str) or len(password) < 4:
        raise ValueError("Пароль должен быть не короче 4 символов")

    username = username.strip()
    users = load_users()

    if any(item["username"].casefold() == username.casefold() for item in users):
        raise ValueError(f"Имя пользователя '{username}' уже занято")

    user_id = max((item["user_id"] for item in users), default=0) + 1
    salt = secrets.token_hex(16)
    hashed_password = hashlib.sha256((password + salt).encode("utf-8")).hexdigest()
    registration_date = datetime.now(UTC)

    user = User(user_id, username, hashed_password, salt, registration_date)
    users.append(
        {
            "user_id": user.user_id,
            "username": user.username,
            "hashed_password": user.hashed_password,
            "salt": user.salt,
            "registration_date": user.registration_date.isoformat(),
        }
    )

    portfolios = load_portfolios()
    portfolios.append({"user_id": user.user_id, "wallets": {}})

    save_users(users)
    save_portfolios(portfolios)
    return user


def login(username: str, password: str) -> User:
    """Найти пользователя и проверить его пароль."""
    if not isinstance(username, str) or not username.strip():
        raise ValueError("Имя пользователя не может быть пустым")

    for item in load_users():
        if item["username"].casefold() == username.strip().casefold():
            user = User(
                item["user_id"],
                item["username"],
                item["hashed_password"],
                item["salt"],
                datetime.fromisoformat(item["registration_date"]),
            )
            if not user.verify_password(password):
                raise ValueError("Неверный пароль")
            return user

    raise ValueError(f"Пользователь '{username}' не найден")


def get_portfolio(user: User) -> Portfolio:
    """Загрузить портфель пользователя из JSON-файла."""
    for item in load_portfolios():
        if item["user_id"] == user.user_id:
            wallets = {}
            for code, wallet_data in item["wallets"].items():
                wallets[code] = Wallet(code, wallet_data["balance"])

            return Portfolio(user, wallets)

    raise ValueError(f"Портфель пользователя '{user.username}' не найден")


def get_portfolio_values(
    user: User,
    base_currency: str = "USD",
) -> tuple[list[tuple[str, float, float]], float]:
    """Вернуть балансы, их стоимость и общий итог."""
    try:
        base_code = get_currency(base_currency).code
    except ValueError as error:
        raise ValueError(
            f"Неизвестная базовая валюта '{base_currency}'"
        ) from error

    portfolio = get_portfolio(user)
    total = portfolio.get_total_value(base_code)
    rows = []

    for code, wallet in sorted(portfolio.wallets.items()):
        one_wallet = Portfolio(user, {code: wallet})
        value = one_wallet.get_total_value(base_code)
        rows.append((code, wallet.balance, value))

    return rows, total


@log_action("BUY", verbose=True)
def buy(user: User, currency_code: str, amount: float) -> tuple[float, float, float]:
    """Купить валюту и сохранить новый баланс кошелька."""
    code = get_currency(currency_code).code
    purchase = Wallet(code)
    purchase.deposit(amount)

    estimated_usd = Portfolio(user, {code: purchase}).get_total_value("USD")

    portfolio = get_portfolio(user)
    if code in portfolio.wallets:
        wallet = portfolio.get_wallet(code)
    else:
        wallet = portfolio.add_currency(code)

    previous_balance = wallet.balance
    wallet.deposit(amount)

    portfolios = load_portfolios()
    for item in portfolios:
        if item["user_id"] == user.user_id:
            item["wallets"][code] = {"balance": wallet.balance}
            save_portfolios(portfolios)
            return previous_balance, wallet.balance, estimated_usd

    raise ValueError(f"Портфель пользователя '{user.username}' не найден")


@log_action("SELL", verbose=True)
def sell(user: User, currency_code: str, amount: float) -> tuple[float, float, float]:
    """Продать валюту и сохранить новый баланс кошелька."""
    code = get_currency(currency_code).code
    sale = Wallet(code)
    sale.deposit(amount)

    portfolio = get_portfolio(user)
    if code not in portfolio.wallets:
        raise ValueError(f"У вас нет кошелька '{code}'")

    wallet = portfolio.get_wallet(code)
    if amount > wallet.balance:
        raise InsufficientFundsError(wallet.balance, amount, code)

    estimated_usd = Portfolio(user, {code: sale}).get_total_value("USD")
    previous_balance = wallet.balance
    wallet.withdraw(amount)

    portfolios = load_portfolios()
    for item in portfolios:
        if item["user_id"] == user.user_id:
            item["wallets"][code] = {"balance": wallet.balance}
            save_portfolios(portfolios)
            return previous_balance, wallet.balance, estimated_usd

    raise ValueError(f"Портфель пользователя '{user.username}' не найден")
