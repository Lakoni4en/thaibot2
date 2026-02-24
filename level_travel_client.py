from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, List
import json
import re

import httpx

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
    Клиент, который тянет HTML Level Travel по шаблону ссылки и вытаскивает из
    встроенного JSON данные о турах.
    """

    BASE_URL = "https://level.travel/search"

    def __init__(self, config: BotConfig) -> None:
        self._config = config
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            timeout=30,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                )
            },
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def search_tours(self) -> List[Tour]:
        """
        Ищет туры Москва → Паттайя за весь март 2026 года.
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
        Загружает страницу поиска для конкретной даты и вытаскивает туры
        из встроенного JSON (`__NEXT_DATA__` или похожего объекта).
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
        data = self._extract_embedded_json(html)
        if data is None:
            return []

        return self._parse_json_tours(data, departure_date)

    def _extract_embedded_json(self, html: str) -> Any | None:
        """
        Пытается вытащить большой JSON, который фронт кладёт в <script>.

        Часто это что-то вроде:
        <script id="__NEXT_DATA__" type="application/json">{"props": ...}</script>
        или window.__INITIAL_STATE__ = {...};
        """

        # Попытка 1: <script id="__NEXT_DATA__" type="application/json">...</script>
        m = re.search(
            r'<script[^>]+id="__NEXT_DATA__"[^>]*>(\{.*?\})</script>',
            html,
            re.DOTALL,
        )
        if m:
            try:
                return json.loads(m.group(1))
            except Exception:
                pass

        # Попытка 2: window.__INITIAL_STATE__ = {...};
        m = re.search(
            r"window\.__INITIAL_STATE__\s*=\s*(\{.*?\})\s*;</",
            html,
            re.DOTALL,
        )
        if m:
            chunk = m.group(1)
            try:
                return json.loads(chunk)
            except Exception:
                pass

        return None

    def _parse_json_tours(self, data: Any, departure_date: str) -> List[Tour]:
        """
        Рекурсивно обходит JSON и вытаскивает объекты, похожие на туры.
        Т.к. точная структура неизвестна, ищем словари с полями про отель/цену/ночи.
        """

        found: List[Tour] = []

        def walk(node: Any) -> None:
            if isinstance(node, dict):
                # эвристика: есть поля про отель + ночи + цену
                keys = set(node.keys())
                has_nights = "nights" in keys or "duration" in keys
                has_price = "price" in keys or "totalPrice" in keys
                has_hotel = (
                    "hotelName" in keys
                    or "hotel" in keys
                    or "hotel_name" in keys
                )

                if has_nights and has_price and has_hotel:
                    try:
                        hotel_name = (
                            node.get("hotelName")
                            or node.get("hotel_name")
                            or (
                                isinstance(node.get("hotel"), dict)
                                and node["hotel"].get("name")
                            )
                            or "Отель"
                        )

                        nights_val = node.get("nights") or node.get("duration") or 0
                        nights = int(nights_val)

                        price_obj = node.get("price") or node.get("totalPrice") or {}
                        if isinstance(price_obj, dict):
                            amount = price_obj.get("amount") or price_obj.get(
                                "value", 0
                            )
                            currency = price_obj.get("currency", "RUB")
                        else:
                            amount = price_obj
                            currency = "RUB"

                        price = int(amount or 0)

                        link = (
                            node.get("url")
                            or node.get("deepLink")
                            or node.get("deeplink")
                            or ""
                        )
                        if link and link.startswith("/"):
                            link = f"https://level.travel{link}"

                        if not (self._config.min_nights <= nights <= self._config.max_nights):
                            return

                        found.append(
                            Tour(
                                hotel_name=str(hotel_name),
                                nights=nights,
                                price=price,
                                currency=str(currency),
                                departure_date=departure_date,
                                flight_is_direct=self._config.direct_only,
                                url=link,
                            )
                        )
                        return
                    except Exception:
                        # если не удалось распарсить как тур — идём дальше внутрь
                        pass

                for v in node.values():
                    walk(v)

            elif isinstance(node, list):
                for item in node:
                    walk(item)

        walk(data)
        return found

