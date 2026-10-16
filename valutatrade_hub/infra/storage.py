import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def load_users() -> list[dict]:
    """Прочитать список пользователей из JSON-файла."""
    path = DATA_DIR / "users.json"

    if not path.exists():
        return []

    data = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(data, list):
        raise TypeError("В users.json должен находиться список пользователей")

    return data


def save_users(users: list[dict]) -> None:
    """Сохранить список пользователей в JSON-файл."""
    if not isinstance(users, list):
        raise TypeError("Пользователи должны быть переданы списком")

    path = DATA_DIR / "users.json"
    content = json.dumps(users, ensure_ascii=False, indent=2) + "\n"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def load_portfolios() -> list[dict]:
    """Прочитать список портфелей из JSON-файла."""
    path = DATA_DIR / "portfolios.json"

    if not path.exists():
        return []

    data = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(data, list):
        raise TypeError("В portfolios.json должен находиться список портфелей")

    return data


def save_portfolios(portfolios: list[dict]) -> None:
    """Сохранить список портфелей в JSON-файл."""
    if not isinstance(portfolios, list):
        raise TypeError("Портфели должны быть переданы списком")

    path = DATA_DIR / "portfolios.json"
    content = json.dumps(portfolios, ensure_ascii=False, indent=2) + "\n"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")