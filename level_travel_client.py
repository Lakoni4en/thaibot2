from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import List

import httpx
from bs4 import BeautifulSoup

from config import BotConfig


@dataclass
class Tour:
    hotel_name: str
    nights: int
    price: int
    currency: str
    departure_date: str
    flight_is_direct: bool
    url: str


class LevelTravelClient:
    """
    Клиент, который парсит HTML Level Travel по шаблону ссылки из браузера.

    Используем публичную страницу поиска, например:
    https://level.travel/search/Moscow-RU-to-Pattaya-TH-departure-10.03.2026-for-10-nights-2-adults-0-kids-1..5-stars-package-type?filter_direct_flight=true
    """

    BASE_URL = "https://level.travel/search"

    def __init__(self, config: BotConfig) -> None:
        self._config = config
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=20,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def search_tours(self) -> List[Tour]:
        """
        Ищет туры Москва → Паттайя за весь март 2026 года.

        Диапазон дат и длительность (ночей) захардкожены под задачу:
        - март 2026 (1–31 число);
        - 10–15 ночей;
        - только прямые рейсы (filter_direct_flight=true в URL).
        """

        start = date(2026, 3, 1)
        end = date(2026, 3, 31)

        all_tours: List[Tour] = []
        current = start
        while current <= end:
            dep_str = current.strftime("%d.%m.%Y")
            daily_tours = await self._fetch_tours_for_date(dep_str)
            all_tours.extend(daily_tours)
            current += timedelta(days=1)

        return all_tours

    async def _fetch_tours_for_date(self, departure_date: str) -> List[Tour]:
        """
        Загружает страницу поиска для конкретной даты и вытаскивает оттуда туры.

        URL собирается по тому же шаблону, что и в присланной ссылке.
        """

        path = (
            f"/Moscow-RU-to-Pattaya-TH-departure-{departure_date}-"
            f"for-10-nights-2-adults-0-kids-1..5-stars-package-type"
        )
        params = {"filter_direct_flight": "true"} if self._config.direct_only else {}

        try:
            resp = await self._client.get(path, params=params)
            resp.raise_for_status()
        except Exception:
            return []

        html = resp.text
        return self._parse_html(html, departure_date)

    def _parse_html(self, html: str, departure_date: str) -> List[Tour]:
        """
        Грубый парсер HTML результата поиска.

        Селекторы подобраны примерно и могут потребовать корректировки,
        если разметка Level Travel изменится.
        """

        soup = BeautifulSoup(html, "html.parser")
        tours: List[Tour] = []

        # ПРИМЕР: ищем карточки туров. Класс нужно уточнить в реальной разметке.
        cards = soup.find_all("div", class_="tour-card")

        for card in cards:
            try:
                hotel_el = card.find("h2") or card.find("h3")
                hotel_name = hotel_el.get_text(strip=True) if hotel_el else "Отель"

                nights_text_el = card.find(string=lambda t: t and "ноч" in t)
                nights = 0
                if nights_text_el:
                    digits = "".join(ch for ch in nights_text_el if ch.isdigit())
                    nights = int(digits or 0)

                price_el = card.find("span", class_="price") or card.find(
                    string=lambda t: t and "₽" in t
                )
                price = 0
                currency = "RUB"
                if price_el:
                    text = (
                        price_el.get_text(strip=True)
                        if hasattr(price_el, "get_text")
                        else str(price_el)
                    )
                    digits = "".join(ch for ch in text if ch.isdigit())
                    if digits:
                        price = int(digits)

                link_el = card.find("a", href=True)
                url = link_el["href"] if link_el else ""
                if url and url.startswith("/"):
                    url = f"https://level.travel{url}"

                is_direct = True  # уже фильтруем по filter_direct_flight=true

                if not (self._config.min_nights <= nights <= self._config.max_nights):
                    continue

                tours.append(
                    Tour(
                        hotel_name=hotel_name,
                        nights=nights,
                        price=price,
                        currency=currency,
                        departure_date=departure_date,
                        flight_is_direct=is_direct,
                        url=url,
                    )
                )
            except Exception:
                continue

        return tours

