## Telegram-бот для отслеживания туров Москва → Паттайя (Level Travel)

Этот проект — Telegram-бот, который ищет туры в Паттайю из Москвы,
парся публичную страницу поиска Level Travel по ссылке вида:

`https://level.travel/search/Moscow-RU-to-Pattaya-TH-departure-10.03.2026-for-10-nights-2-adults-0-kids-1..5-stars-package-type?filter_direct_flight=true`

Бот перебирает все даты **марта 2026 года** и для каждой даты открывает такую страницу.
Фильтрует туры по:

- **Длительности**: от 10 до 15 ночей (диапазон задаётся в переменных окружения)
- **Типу перелёта**: только **прямые рейсы**

Фильтры по умолчанию жёстко зашиты в конфигурации, но легко меняются при необходимости.

---

### Стек

- **Python 3.10+**
- **aiogram 3** — Telegram-бот
- **httpx** — HTTP‑клиент для запросов на Level Travel
- **beautifulsoup4** — парсинг HTML
- **python-dotenv** — загрузка настроек из `.env`

---

### Установка и запуск локально

1. Установите зависимости:

```bash
cd THAI
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. Создайте файл `.env` в корне проекта (там же, где `bot.py`) со своими ключами:

```env
TELEGRAM_BOT_TOKEN=ВАШ_ТОКЕН_ОТ_BOTFATHER

# Фильтры по умолчанию
ORIGIN_CITY_CODE=MOW      # код города вылета (Москва, используется в тексте)
DESTINATION_CITY_CODE=UTP # код Паттайи (используется в тексте)
MIN_NIGHTS=10
MAX_NIGHTS=15
DIRECT_ONLY=true          # только прямые рейсы
```

3. Запустите бота:

```bash
python bot.py
```

В Телеграме:

- `/start` — приветствие и описание фильтров
- `/tours` — поиск туров Москва → Паттайя на весь март 2026 c фильтром 10–15 ночей и только прямые рейсы

---

### Как устроен парсинг Level Travel

Файл `level_travel_client.py`:

- собирает URL по тому же шаблону, что и в браузере (см. пример выше);
- перебирает все даты с 1 по 31 марта 2026;
- для каждой даты качает HTML и с помощью `beautifulsoup4` пытается найти карточки туров
  (селектор `div.tour-card`, заголовок отеля, цену, количество ночей и ссылку).

Разметка сайта может меняться, поэтому при необходимости:

1. Откройте страницу поиска в браузере.
2. Через "Просмотр кода" найдите классы карточек туров, цены и ночей.
3. Обновите селекторы в методе `_parse_html` внутри `level_travel_client.py`.

---

### Загрузка на GitHub

1. В корне проекта (папка `THAI`) выполните:

```bash
git init
git add .
git commit -m "Initial commit: Pattaya tours Telegram bot"
git branch -M main
git remote add origin https://github.com/ВАШ_ЛОГИН/ИМЯ_РЕПО.git
git push -u origin main
```

2. Не коммитьте файл `.env` (лучше заранее добавить его в `.gitignore`).

