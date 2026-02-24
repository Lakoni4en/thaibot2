import asyncio
from textwrap import shorten

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message

from config import get_config
from level_travel_client import LevelTravelClient


async def format_tour_message(tour) -> str:
    """Форматирует один тур в текст для отправки в Telegram."""
    hotel = shorten(tour.hotel_name, width=50, placeholder="…")
    price_str = f"{tour.price:,} {tour.currency}".replace(",", " ")
    direct_str = "Прямой рейс ✅" if tour.flight_is_direct else "С пересадками"

    lines = [
        f"🏨 {hotel}",
        f"📅 Вылет: {tour.departure_date}",
        f"🌙 Ночей: {tour.nights}",
        f"💰 Цена: {price_str}",
        f"✈️ {direct_str}",
    ]
    if tour.url:
        lines.append(f"🔗 Ссылка: {tour.url}")

    return "\n".join(lines)


async def main() -> None:
    config = get_config()
    bot = Bot(token=config.telegram_token, parse_mode="HTML")
    dp = Dispatcher()
    lt_client = LevelTravelClient(config)

    @dp.message(CommandStart())
    async def cmd_start(message: Message) -> None:
        text = (
            "Привет! 👋\n\n"
            "Я бот, который ищет перелёты/туры в Паттайю из Москвы через Aviasales (Travelpayouts).\n"
            f"Фильтр вшит в код: от <b>{config.min_nights}</b> до "
            f"<b>{config.max_nights}</b> ночей, только <b>прямые рейсы</b>,\n"
            "и поиск идёт по всем датам <b>марта 2026 года</b>.\n\n"
            "Отправь команду /tours, чтобы посмотреть актуальные предложения."
        )
        await message.answer(text)

    @dp.message(Command("tours"))
    async def cmd_tours(message: Message) -> None:
        await message.answer(
            "Ищу подходящие перелёты в Паттайю за весь март 2026 через Aviasales.\n"
            "Это может занять до минуты, подождите…"
        )

        try:
            tours = await lt_client.search_tours()
        except Exception as exc:
            await message.answer(
                "Не удалось получить данные о перелётах из внешнего API. "
                "Проверьте AVIASALES_TOKEN и параметры в конфигурации.\n"
                f"<code>{exc}</code>"
            )
            return

        if not tours:
            await message.answer(
                "Сейчас нет туров Москва → Паттайя, которые подходят под фильтр "
                f"{config.min_nights}-{config.max_nights} ночей и только прямые рейсы."
            )
            return

        # Ограничим количество отправляемых туров, чтобы не спамить
        max_to_show = 5
        for tour in tours[:max_to_show]:
            text = await format_tour_message(tour)
            await message.answer(text)

        if len(tours) > max_to_show:
            await message.answer(
                f"Показано {max_to_show} лучших вариантов из {len(tours)}. "
                "Сузьте условия или смотрите остальные по ссылке из предложения."
            )

    try:
        await dp.start_polling(bot)
    finally:
        await lt_client.close()


if __name__ == "__main__":
    asyncio.run(main())

