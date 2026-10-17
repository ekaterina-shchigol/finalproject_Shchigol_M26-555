from datetime import UTC, datetime
from math import isfinite

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.infra.database import DatabaseManager


class RatesStorage:
    """Сохранять текущие курсы и историю измерений."""

    def __init__(self) -> None:
        self.database = DatabaseManager()

    def save_rates(self, new_rates: dict[str, dict]) -> int:
        """Сохранить новые измерения и вернуть число обновлённых пар."""
        if not new_rates:
            return 0

        cache = self.database.read_object("rates_file")
        pairs = cache.get("pairs", {})
        if not isinstance(pairs, dict):
            raise ApiRequestError("Неверный формат локального кэша курсов")

        history = self.database.read_list("history_file")
        known_ids = {record["id"] for record in history}
        updated_count = 0

        for pair, entry in new_rates.items():
            rate = entry.get("rate")
            timestamp = entry.get("updated_at")
            source = entry.get("source")

            if (
                isinstance(rate, bool)
                or not isinstance(rate, (int, float))
                or not isfinite(rate)
                or rate <= 0
                or not isinstance(timestamp, str)
                or not isinstance(source, str)
            ):
                raise ApiRequestError(f"Неверные данные курса {pair}")

            try:
                new_time = datetime.fromisoformat(timestamp)
            except ValueError as error:
                raise ApiRequestError(
                    f"Неверная дата курса {pair}"
                ) from error

            if new_time.tzinfo is None:
                raise ApiRequestError(f"Нет часового пояса у курса {pair}")

            record_id = f"{pair}_{new_time.astimezone(UTC).isoformat()}"
            if record_id not in known_ids:
                history.append(
                    {
                        "id": record_id,
                        "from_currency": pair.split("_")[0],
                        "to_currency": pair.split("_")[1],
                        "rate": float(rate),
                        "timestamp": timestamp,
                        "source": source,
                        "meta": entry.get("meta", {}),
                    }
                )
                known_ids.add(record_id)

            current = pairs.get(pair)
            current_time = None
            if isinstance(current, dict):
                current_timestamp = current.get("updated_at")
                if isinstance(current_timestamp, str):
                    try:
                        current_time = datetime.fromisoformat(
                            current_timestamp
                        )
                    except ValueError:
                        pass

            if current_time is None or new_time > current_time:
                pairs[pair] = {
                    "rate": float(rate),
                    "updated_at": timestamp,
                    "source": source,
                }
                updated_count += 1

        cache["pairs"] = pairs
        cache["last_refresh"] = datetime.now(UTC).isoformat()

        # Каждый файл заменяется целиком; общий момент замены для двух
        # отдельных файлов файловая система не гарантирует.
        self.database.write_list("history_file", history)
        self.database.write_object("rates_file", cache)
        return updated_count