## Telegram-бот для отслеживания туров Москва → Паттайя (Level Travel)

Этот проект — Telegram-бот, который ищет варианты перелёта/тура в Паттайю из Москвы
через **официальный API Kiwi Tequila** (а не Level Travel).

Бот запрашивает рейсы Москва → Паттайя (UTP) за **весь март 2026 года** и фильтрует их по:

- **Длительности**: от 10 до 15 ночей (диапазон задаётся в переменных окружения)
- **Типу перелёта**: только **прямые рейсы**

Фильтры по умолчанию жёстко зашиты в конфигурации, но легко меняются при необходимости.

---

### Стек

- **Python 3.10+**
- **aiogram 3** — Telegram-бот
- **httpx** — HTTP‑клиент для запросов к Kiwi Tequila API
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
KIWI_API_KEY=ВАШ_API_КЛЮЧ_TEQUILA

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
- `/tours` — поиск перелётов Москва → Паттайя на весь март 2026 c фильтром 10–15 ночей и только прямые рейсы

---

### Как устроен запрос к Kiwi Tequila

Файл `level_travel_client.py`:

- отправляет запрос на `https://api.tequila.kiwi.com/v2/search` с параметрами:
  - `fly_from=MOW` (Москва),
  - `fly_to=UTP` (U-Tapao, рядом с Паттайей),
  - `date_from=01/03/2026`, `date_to=31/03/2026`,
  - `nights_in_dst_from=10`, `nights_in_dst_to=15`,
  - только прямые рейсы (через `max_stopovers=0`, если `DIRECT_ONLY=true`);
- из ответа собирает список вариантов: маршрут, дата вылета, количество ночей, цена и `deep_link`
  (ссылка на бронирование/детали перелёта на стороне Kiwi);
- дополнительно фильтрует по количеству ночей и прямым рейсам, чтобы строго соблюдать условия 10–15 ночей и без пересадок.

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

