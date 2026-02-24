from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import List

import httpx

from config import BotConfig


@dataclass
class Tour:
    """
    Объект тура/перелёта.

    Мы используем публичное API Kiwi (Skypicker), которое возвращает перелёты
    Москва → Паттайя. Каждый объект в списке трактуем как "тур":
    - город вылета / прилёта;
    - даты вылета и возвращения;
    - цена;
    - ссылка на бронирование.
    """

    hotel_name: str  # здесь будет описание перелёта
    nights: int
    price: int
    currency: str
    departure_date: str
    flight_is_direct: bool
    url: str


class LevelTravelClient:
    """
    Вместо Level Travel используем бесплатный партнёрский API Aviasales / Travelpayouts.

    Документация: https://travelpayouts.github.io/slate/#prices_for_dates
    Эндпоинт поиска: /aviasales/v3/prices_for_dates
    Требуется токен AVIASALES_TOKEN (X-Access-Token).
    """

    BASE_URL = "https://api.travelpayouts.com/aviasales/v3/prices_for_dates"

    def __init__(self, config: BotConfig) -> None:
        self._config = config
        self._client = httpx.AsyncClient(
            timeout=30,
            headers={
                "accept": "application/json",
                "X-Access-Token": config.aviasales_token,
            },
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def search_tours(self) -> List[Tour]:
        """
        Ищет прямые перелёты Москва → Паттайя (UTP) на весь март 2026 года.
        Travelpayouts возвращает цены по датам вылета, мы дополнительно
        фильтруем по длительности пребывания (ночей) и прямым рейсам.
        """

        date_from = date(2026, 3, 1)
        date_to = date(2026, 3, 31)

        params = {
            "origin": "MOW",  # Москва
            "destination": "UTP",  # U-Tapao (Паттайя)
            "departure_at": f"{date_from:%Y-%m-%d}:{date_to:%Y-%m-%d}",
            "one_way": "false",
            "direct": "true" if self._config.direct_only else "false",
            "limit": 30,
            # Aviasales/Travelpayouts также принимает токен как query-параметр `token`
            "token": self._config.aviasales_token,
        }

        resp = await self._client.get(self.BASE_URL, params=params)
        resp.raise_for_status()
        raw = resp.json()

        flights = raw.get("data", []) or []
        tours: List[Tour] = []

        for f in flights:
            try:
                price = int(f.get("price", 0))
                currency = raw.get("currency", "EUR")

                # Кол-во ночей в точке назначения
                nights = int(f.get("nightsInDest", 0))
                if not (self._config.min_nights <= nights <= self._config.max_nights):
                    continue

                # Маршрут (список сегментов)
                route = f.get("route") or []
                is_direct = len(route) == 1
                if self._config.direct_only and not is_direct:
                    continue

                city_from = f.get("cityFrom") or f.get("flyFrom") or "Москва"
                city_to = f.get("cityTo") or f.get("flyTo") or "Паттайя"
                local_departure = f.get("local_departure", "")[:10]  # YYYY-MM-DD

                airlines = {seg.get("airline", "") for seg in route}
                airlines_str = ", ".join(sorted(a for a in airlines if a)) or "авиакомпания"

                title = f"{city_from} → {city_to} ({airlines_str})"

                deep_link = f.get("deep_link") or ""

                tours.append(
                    Tour(
                        hotel_name=title,
                        nights=nights,
                        price=price,
                        currency=currency,
                        departure_date=local_departure,
                        flight_is_direct=is_direct,
                        url=deep_link,
                    )
                )
            except Exception:
                continue

        return tours

