import os
from dataclasses import dataclass, field
from pathlib import Path

from valutatrade_hub.infra.database import DatabaseManager


@dataclass
class ParserConfig:
    """Настройки источников курсов и файлов парсера."""

    exchangerate_api_key: str | None = field(
        default_factory=lambda: os.getenv("EXCHANGERATE_API_KEY")
    )
    coingecko_api_key: str | None = field(
        default_factory=lambda: os.getenv("COINGECKO_API_KEY")
    )

    coingecko_url: str = "https://api.coingecko.com/api/v3/simple/price"
    exchangerate_api_url: str = "https://v6.exchangerate-api.com/v6"

    base_currency: str = "USD"
    fiat_currencies: tuple[str, ...] = ("EUR", "GBP", "RUB")
    crypto_currencies: tuple[str, ...] = ("BTC", "ETH", "SOL")
    crypto_id_map: dict[str, str] = field(
        default_factory=lambda: {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "SOL": "solana",
        }
    )

    rates_file_path: Path = field(
        default_factory=lambda: DatabaseManager().path_for("rates_file")
    )
    history_file_path: Path = field(
        default_factory=lambda: DatabaseManager().path_for("history_file")
    )
    request_timeout: int = 10