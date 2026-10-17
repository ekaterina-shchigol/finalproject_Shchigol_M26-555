import json
import os
import tempfile
from pathlib import Path
from typing import Self

from valutatrade_hub.infra.settings import SettingsLoader


class DatabaseManager:
    """Единый экземпляр для доступа к JSON-файлам проекта."""

    _instance: "DatabaseManager | None" = None

    def __new__(cls) -> Self:
        # __new__ сохраняет один экземпляр для всех обращений к данным.
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._settings = SettingsLoader()
        return cls._instance

    def path_for(self, setting_name: str) -> Path:
        """Вернуть абсолютный путь к файлу из настроек."""
        relative_path = self._settings.get(setting_name)
        if not isinstance(relative_path, str):
            raise TypeError(f"Путь в настройках должен быть строкой: {setting_name}")
        project_root = Path(__file__).resolve().parents[2]
        return project_root / relative_path

    def read_list(self, setting_name: str) -> list[dict]:
        """Прочитать из JSON список записей; отсутствующий файл считать пустым."""
        path = self.path_for(setting_name)
        if not path.exists():
            return []

        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise TypeError(f"В файле {path.name} должен находиться список")

        return data

    def read_object(self, setting_name: str) -> dict:
        """Прочитать JSON-объект; отсутствующий файл считать пустым."""
        path = self.path_for(setting_name)
        if not path.exists():
            return {}

        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise TypeError(f"В файле {path.name} должен находиться объект")

        return data

    def write_list(self, setting_name: str, records: list[dict]) -> None:
        """Атомарно сохранить список записей в JSON."""
        if not isinstance(records, list):
            raise TypeError("Данные для сохранения должны быть списком")

        path = self.path_for(setting_name)
        path.parent.mkdir(parents=True, exist_ok=True)
        content = json.dumps(records, ensure_ascii=False, indent=2) + "\n"

        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            delete=False,
        ) as temporary_file:
            temporary_file.write(content)
            temporary_path = Path(temporary_file.name)

        try:
            os.replace(temporary_path, path)
        finally:
            temporary_path.unlink(missing_ok=True)
