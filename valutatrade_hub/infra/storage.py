from valutatrade_hub.infra.database import DatabaseManager


def load_users() -> list[dict]:
    """Прочитать пользователей из JSON."""
    return DatabaseManager().read_list("users_file")


def save_users(users: list[dict]) -> None:
    """Сохранить пользователей в JSON."""
    DatabaseManager().write_list("users_file", users)


def load_portfolios() -> list[dict]:
    """Прочитать портфели из JSON."""
    return DatabaseManager().read_list("portfolios_file")


def save_portfolios(portfolios: list[dict]) -> None:
    """Сохранить портфели в JSON."""
    DatabaseManager().write_list("portfolios_file", portfolios)