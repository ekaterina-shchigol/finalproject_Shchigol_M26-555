import tomllib
from pathlib import Path
from typing import Any, Self


class SettingsLoader:
    """Единый экземпляр с настройками приложения."""

    _instance: "SettingsLoader | None" = None

    def __new__(cls) -> Self:
        # __new__ позволяет вернуть уже созданный экземпляр.
        if cls._instance is None:
            config_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
            with config_path.open("rb") as config_file:
                values = tomllib.load(config_file)["tool"]["valutatrade"]

            cls._instance = super().__new__(cls)
            cls._instance._values = values
        return cls._instance

    def get(self, key: str, default: Any = None) -> Any:
        """Вернуть настройку или значение по умолчанию."""
        return self._values.get(key, default)