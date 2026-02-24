import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


@dataclass
class BotConfig:
    telegram_token: str
    aviasales_token: str
    origin_city_code: str
    destination_city_code: str
    min_nights: int
    max_nights: int
    direct_only: bool


def get_config() -> BotConfig:
    """Загружает конфигурацию бота из переменных окружения."""

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("Не задан TELEGRAM_BOT_TOKEN в .env или переменных окружения")

    aviasales_token = os.getenv("AVIASALES_TOKEN")
    if not aviasales_token:
        raise RuntimeError("Не задан AVIASALES_TOKEN в .env или переменных окружения")

    origin = os.getenv("ORIGIN_CITY_CODE", "MOW")
    destination = os.getenv("DESTINATION_CITY_CODE", "UTP")

    min_nights = int(os.getenv("MIN_NIGHTS", "10"))
    max_nights = int(os.getenv("MAX_NIGHTS", "15"))

    direct_only = os.getenv("DIRECT_ONLY", "true").lower() == "true"

    return BotConfig(
        telegram_token=token,
        aviasales_token=aviasales_token,
        origin_city_code=origin,
        destination_city_code=destination,
        min_nights=min_nights,
        max_nights=max_nights,
        direct_only=direct_only,
    )

