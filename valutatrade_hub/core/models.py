import hashlib
from datetime import datetime
from math import isfinite

from valutatrade_hub.core.utils import DEMO_USD_RATES


class Wallet:
    """Кошелёк для одной валюты."""

    def __init__(self, currency_code: str, balance: float = 0.0) -> None:
        if not isinstance(currency_code, str) or not currency_code.strip():
            raise ValueError("Код валюты не может быть пустым")

        self.currency_code = currency_code.strip().upper()
        self._balance = 0.0
        self.balance = balance

    @property
    def balance(self) -> float:
        """Вернуть текущий баланс."""
        return self._balance

    @balance.setter
    def balance(self, value: float) -> None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError("Баланс должен быть числом")
        if not isfinite(value) or value < 0:
            raise ValueError("Баланс должен быть конечным неотрицательным числом")

        self._balance = float(value)
    
    def deposit(self, amount: float) -> None:
        """Пополнить баланс на положительную сумму."""
        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            raise TypeError("Сумма пополнения должна быть числом")
        if not isfinite(amount) or amount <= 0:
            raise ValueError("Сумма пополнения должна быть положительным числом")

        self.balance = self.balance + amount

    def withdraw(self, amount: float) -> None:
        """Списать положительную сумму с баланса."""
        if isinstance(amount, bool) or not isinstance(amount, (int, float)):
            raise TypeError("Сумма списания должна быть числом")
        if not isfinite(amount) or amount <= 0:
            raise ValueError("Сумма списания должна быть положительным числом")
        if amount > self.balance:
            raise ValueError("Недостаточно средств на балансе")

        self.balance = self.balance - amount

    def get_balance_info(self) -> str:
        """Вернуть код валюты и текущий баланс."""
        return f"{self.currency_code}: {self.balance:.2f}"


class User:
    """Пользователь платформы."""

    def __init__(
        self,
        user_id: int,
        username: str,
        hashed_password: str,
        salt: str,
        registration_date: datetime,
    ) -> None:
        if isinstance(user_id, bool) or not isinstance(user_id, int) or user_id <= 0:
            raise ValueError("Идентификатор пользователя должен быть положительным целым числом")
        if not isinstance(username, str) or not username.strip():
            raise ValueError("Имя пользователя не может быть пустым")
        if not isinstance(hashed_password, str) or not hashed_password:
            raise ValueError("Хеш пароля не может быть пустым")
        if not isinstance(salt, str) or not salt:
            raise ValueError("Соль не может быть пустой")
        if not isinstance(registration_date, datetime):
            raise TypeError("Дата регистрации должна иметь тип datetime")

        self._user_id = user_id
        self._username = username.strip()
        self._hashed_password = hashed_password
        self._salt = salt
        self._registration_date = registration_date

    @property
    def user_id(self) -> int:
        """Вернуть идентификатор пользователя."""
        return self._user_id

    @property
    def username(self) -> str:
        """Вернуть имя пользователя."""
        return self._username

    @username.setter
    def username(self, value: str) -> None:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Имя пользователя не может быть пустым")

        self._username = value.strip()        

    @property
    def hashed_password(self) -> str:
        """Вернуть хеш пароля для сохранения пользователя."""
        return self._hashed_password

    @property
    def salt(self) -> str:
        """Вернуть соль для сохранения пользователя."""
        return self._salt

    @property
    def registration_date(self) -> datetime:
        """Вернуть дату регистрации."""
        return self._registration_date

    def verify_password(self, password: str) -> bool:
        """Проверить введённый пароль."""
        if not isinstance(password, str):
            return False

        candidate_hash = hashlib.sha256(
            (password + self._salt).encode("utf-8")
        ).hexdigest()
        return candidate_hash == self._hashed_password

    def change_password(self, new_password: str) -> None:
        """Изменить пароль пользователя."""
        if not isinstance(new_password, str) or len(new_password) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов")

        self._hashed_password = hashlib.sha256(
            (new_password + self._salt).encode("utf-8")
        ).hexdigest()

    def get_user_info(self) -> dict[str, int | str]:
        """Вернуть общедоступную информацию о пользователе."""
        return {
            "user_id": self._user_id,
            "username": self._username,
            "registration_date": self._registration_date.isoformat(),
        }


class Portfolio:
    """Набор валютных кошельков одного пользователя."""

    def __init__(
        self,
        user: User,
        wallets: dict[str, Wallet] | None = None,
    ) -> None:
        if not isinstance(user, User):
            raise TypeError("Для портфеля нужен объект User")
        if wallets is not None and not isinstance(wallets, dict):
            raise TypeError("Кошельки должны быть словарём")

        self._user = user
        self._user_id = user.user_id
        self._wallets = dict(wallets) if wallets is not None else {}

    @property
    def user(self) -> User:
        """Вернуть владельца портфеля."""
        return self._user

    @property
    def wallets(self) -> dict[str, Wallet]:
        """Вернуть копию словаря кошельков."""
        return self._wallets.copy()

    def add_currency(self, currency_code: str) -> Wallet:
        """Добавить кошелёк для новой валюты."""
        wallet = Wallet(currency_code)

        if wallet.currency_code in self._wallets:
            raise ValueError(f"Кошелёк '{wallet.currency_code}' уже существует")

        self._wallets[wallet.currency_code] = wallet
        return wallet

    def get_wallet(self, currency_code: str) -> Wallet:
        """Найти кошелёк по коду валюты."""
        if not isinstance(currency_code, str) or not currency_code.strip():
            raise ValueError("Код валюты не может быть пустым")

        code = currency_code.strip().upper()
        if code not in self._wallets:
            raise KeyError(f"Кошелёк '{code}' не найден")

        return self._wallets[code]

    def get_total_value(
        self,
        base_currency: str = "USD",
        exchange_rates: dict[str, float] | None = None,
    ) -> float:
        """Посчитать стоимость портфеля в базовой валюте."""
        rates = (
            exchange_rates
            if exchange_rates is not None
            else DEMO_USD_RATES
        )

        if not isinstance(base_currency, str) or not base_currency.strip():
            raise ValueError("Базовая валюта не может быть пустой")

        base_code = base_currency.strip().upper()
        if base_code not in rates:
            raise ValueError(f"Неизвестная базовая валюта '{base_code}'")

        total_usd = 0.0
        for wallet in self._wallets.values():
            if wallet.currency_code not in rates:
                raise ValueError(f"Нет курса для '{wallet.currency_code}'")
            total_usd += wallet.balance * rates[wallet.currency_code]

        return total_usd / rates[base_code]