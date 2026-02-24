from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
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
        Travelpayouts возвращает цены по конкретной дате вылета, поэтому
        перебираем все дни месяца и агрегируем результаты.
        """

        date_from = date(2026, 3, 1)
        date_to = date(2026, 3, 31)

        tours: List[Tour] = []

        current = date_from
        while current <= date_to:
            params = {
                "origin": "MOW",  # Москва
                "destination": "UTP",  # U-Tapao (Паттайя)
                "departure_at": f"{current:%Y-%m-%d}",
                "one_way": "false",
                "direct": "true" if self._config.direct_only else "false",
                "limit": 30,
                "token": self._config.aviasales_token,
            }

            resp = await self._client.get(self.BASE_URL, params=params)
            resp.raise_for_status()
            raw = resp.json()

            flights = raw.get("data", []) or []

            for f in flights:
                try:
                    # Цена
                    price = int(f.get("value", 0))
                    currency = "RUB"

                    depart_date_str = f.get("depart_date")
                    return_at_str = f.get("return_at")  # формат YYYY-MM-DDTHH:MM:SSZ
                    if not depart_date_str or not return_at_str:
                        continue

                    depart_d = date.fromisoformat(depart_date_str)
                    return_d = date.fromisoformat(return_at_str[:10])
                    nights = (return_d - depart_d).days
                    if nights <= 0:
                        continue

                    if not (self._config.min_nights <= nights <= self._config.max_nights):
                        continue

                    # Прямой рейс – без пересадок
                    changes = int(f.get("number_of_changes", 0))
                    is_direct = changes == 0
                    if self._config.direct_only and not is_direct:
                        continue

                    origin = f.get("origin", "MOW")
                    destination = f.get("destination", "UTP")

                    title = f"{origin} → {destination}"
                    link = f.get("link") or ""

                    tours.append(
                        Tour(
                            hotel_name=title,
                            nights=nights,
                            price=price,
                            currency=currency,
                            departure_date=depart_date_str,
                            flight_is_direct=is_direct,
                            url=link,
                        )
                    )
                except Exception:
                    continue

            current += timedelta(days=1)

        return tours

