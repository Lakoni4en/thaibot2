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
    Вместо Level Travel используем публичный API Kiwi (Skypicker).

    Документация (неофициальная, но общедоступная): `https://api.skypicker.com`.
    Мы строим запрос вида:

    https://api.skypicker.com/flights
        ?fly_from=MOW
        &fly_to=UTP
        &date_from=01/03/2026
        &date_to=31/03/2026
        &nights_in_dst_from=10
        &nights_in_dst_to=15
        &direct_flights=1
        &curr=RUB
        &partner=picky
    """

    BASE_URL = "https://api.skypicker.com/flights"

    def __init__(self, config: BotConfig) -> None:
        self._config = config
        self._client = httpx.AsyncClient(timeout=30)

    async def close(self) -> None:
        await self._client.aclose()

    async def search_tours(self) -> List[Tour]:
        """
        Ищет прямые перелёты Москва → Паттайя на весь март 2026 года
        с длительностью пребывания от min_nights до max_nights.
        """

        # Диапазон дат вылета: весь март 2026
        date_from = date(2026, 3, 1)
        date_to = date(2026, 3, 31)

        params = {
            "fly_from": "MOW",  # Москва
            "fly_to": "UTP",  # U-Tapao (аэропорт рядом с Паттайей)
            "date_from": date_from.strftime("%d/%m/%Y"),
            "date_to": date_to.strftime("%d/%m/%Y"),
            "nights_in_dst_from": self._config.min_nights,
            "nights_in_dst_to": self._config.max_nights,
            "direct_flights": 1 if self._config.direct_only else 0,
            "curr": "RUB",
            "partner": "picky",  # публичный демо-партнёр Kiwi
            "limit": 20,
            "sort": "price",
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

