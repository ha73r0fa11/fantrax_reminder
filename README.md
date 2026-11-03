# Fantrax → Telegram: уведомления о составе

Бот следит за фентези-лигой на [Fantrax](https://www.fantrax.com) и шлёт в
общий Telegram-чат сообщения, когда у команды в **основном составе** (слоты
Active) оказывается игрок, который **не выйдет на поле со старта**.

Определение «не выйдет со старта» (по статусам Fantrax):

| Статус Fantrax | Иконка | Что значит |
|---|---|---|
| Out for next game | `typeId=30` | выбыл, точно не сыграет |
| Suspended | `typeId=6` | дисквалификация, точно не сыграет |
| Late fitness test / Game-time decision | `typeId=1` | под вопросом, может не выйти со старта |

Остальные статусы (в т.ч. «Expected to play») игнорируются. Детекцию легко
расширить — правила лежат в `bot/statuses.py` (список `STATUS_RULES`).

## Как это работает

1. Бот раз в `POLL_INTERVAL_MINUTES` опрашивает неофициальный API Fantrax
   (`POST https://www.fantrax.com/fxpa/req`) — составы всех команд одним
   пакетным запросом.
2. Для каждого игрока в слоте Active смотрит иконки статуса.
3. Если появился новый «проблемный» игрок (или статус изменился — например
   «под вопросом» стал «выбыл»), формирует сообщение и шлёт в чат.
4. Состояние хранится в `state.json` (в Docker — том `bot-data`), чтобы не
   слать повторные уведомления об одном и том же.

## Требования

- Docker (рекомендуется) **или** Python 3.12+ для запуска без Docker.
- Токен Telegram-бота и ID чата.

## Быстрый старт (Docker)

1. Создайте файл `.env` из шаблона:

   ```bash
   cp .env.example .env
   ```

2. Получите токен бота у [@BotFather](https://t.me/BotFather):
   `/newbot` → имя → username → скопируйте токен в `TELEGRAM_BOT_TOKEN`.

3. Узнайте `TELEGRAM_CHAT_ID`:
   - добавьте бота в нужную группу и напишите туда любое сообщение (или
     напишите боту в личку), затем запустите:

     ```bash
     docker compose run --rm fantrax-bot python -m bot.get_chat_id
     ```

   - либо напишите [@userinfobot](https://t.me/userinfobot) в нужном чате.

4. Запустите:

   ```bash
   docker compose up -d --build
   ```

   Логи: `docker compose logs -f fantrax-bot`.

## Запуск без Docker

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate ; Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # заполните токен и chat_id
python -m bot.get_chat_id   # узнать chat_id
python -m bot.main          # цикл проверки
```

Полезные режимы:

```bash
python -m bot.main --once       # одна проверка и выход (для cron)
python -m bot.main --dry-run    # одна проверка без отправки в Telegram
```

## Настройка (переменные окружения)

| Переменная | По умолчанию | Описание |
|---|---|---|
| `FANTRAX_LEAGUE_ID` | `rwoc4s02mrui4mac` | ID лиги из URL |
| `TELEGRAM_BOT_TOKEN` | — | токен бота от @BotFather |
| `TELEGRAM_CHAT_ID` | — | ID чата для уведомлений |
| `POLL_INTERVAL_MINUTES` | `30` | интервал опроса Fantrax |
| `LOG_LEVEL` | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `DRY_RUN` | `false` | `true` — не слать в Telegram, только логировать |
| `STATE_FILE` | `state.json` | путь к файлу состояния (в Docker — `/data/state.json`) |

## Проверка перед запуском

Рекомендую сначала прогнать в режиме «сухого» запуска и посмотреть, что
реально находит бот:

```bash
docker compose run --rm -e DRY_RUN=true fantrax-bot python -m bot.main --once
```

Если статусы определяются не так, как нужно, правила правятся в
`bot/statuses.py`.

## Структура проекта

```
bot/
  config.py       # чтение конфигурации (.env / переменные окружения)
  fantrax.py      # HTTP-клиент к API Fantrax (пакетные запросы)
  statuses.py     # детекция «не выйдет со старта» по иконкам статуса
  notifier.py     # отправка сообщений в Telegram
  state.py        # дедупликация уведомлений (state.json)
  get_chat_id.py  # утилита: узнать chat_id
  main.py         # основной цикл
```

## Важно

- API Fantrax — **неофициальный**. Его структура может измениться без
  предупреждения; если бот перестал получать данные, проверьте
  `docker compose logs`.
- Данные лиги должны быть публичными (в этой лиге они отдаются без логина).
  Если доступ к составам окажется закрыт, потребуется cookie сессии Fantrax.
