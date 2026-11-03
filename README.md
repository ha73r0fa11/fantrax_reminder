# Fantrax → Telegram: уведомления о составе

Бот следит за фентези-лигой на [Fantrax](https://www.fantrax.com) и шлёт
каждому участнику **личное** сообщение, когда у его команды в **основном
составе** (слоты Active) оказывается игрок, который **не выйдет на поле со
старта**.

Кому какое сообщение слать, задаётся ручной таблицей привязки
«команда Fantrax → Telegram chat_id» (файл `mapping.json`).

## Как определяется «не выйдет со старта»

По статусам Fantrax (иконки игрока):

| Статус Fantrax | Иконка | Что значит |
|---|---|---|
| Out for next game | `typeId=30` | выбыл, точно не сыграет |
| Suspended | `typeId=6` | дисквалификация, точно не сыграет |
| Late fitness test / Game-time decision | `typeId=1` | под вопросом, может не выйти со старта |

Остальные статусы (в т.ч. «Expected to play») игнорируются. Правила лежат в
`bot/statuses.py` (список `STATUS_RULES`) и легко расширяются.

## Как это работает

1. Бот раз в `POLL_INTERVAL_MINUTES` опрашивает неофициальный API Fantrax
   (`POST https://www.fantrax.com/fxpa/req`) — составы всех команд одним
   пакетным запросом.
2. Для каждого игрока в слоте Active смотрит иконки статуса.
3. Если появился новый «проблемный» игрок (или статус изменился — например
   «под вопросом» стал «выбыл»), бот шлёт сообщение **владельцу команды**
   согласно `mapping.json`.
4. Состояние хранится в `state.json`, чтобы не слать повторные уведомления.

## Требования

- Docker (рекомендуется) **или** Python 3.12+ для запуска без Docker.
- Токен Telegram-бота.
- chat_id каждого участника (см. ниже).

## Подготовка привязки (mapping.json)

1. Скопируйте шаблон: `cp mapping.example.json mapping.json`.
2. Узнайте chat_id каждого участника:
   - участник пишет боту в личку любое сообщение (или добавляет бота в свою
     группу), затем вы запускаете:

     ```bash
     python -m bot.get_chat_id
     ```

   - либо участник сам пишет [@userinfobot](https://t.me/userinfobot).
3. Впишите в `mapping.json` соответствие. Ключ — название команды (без учёта
   регистра) или её ID, значение — chat_id:

     ```json
     {
       "Fq": 123456789,
       "butep": 987654321,
       "Sognare ✨": -100222333444
     }
     ```

4. Проверить команды и текущую привязку: `python -m bot.mapping`.

## Быстрый старт (Docker)

1. `cp .env.example .env` и впишите `TELEGRAM_BOT_TOKEN` (от
   [@BotFather](https://t.me/BotFather)).
2. `cp mapping.example.json mapping.json` и заполните привязку.
3. Запустите:

   ```bash
   docker compose up -d --build
   ```

   Логи: `docker compose logs -f fantrax-bot`.

Файл `mapping.json` монтируется в контейнер как read-only и читается на каждой
проверке, поэтому правки привязки подхватываются без перезапуска.

## Запуск без Docker

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate ; Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # впишите токен
cp mapping.example.json mapping.json   # заполните привязку
python -m bot.get_chat_id     # узнать chat_id участника
python -m bot.mapping         # проверить привязку
python -m bot.main            # цикл проверки
```

Полезные режимы:

```bash
python -m bot.main --once       # одна проверка и выход (для cron)
python -m bot.main --dry-run    # одна проверка без отправки в Telegram
```

## Развёртывание на сервере (Linux, Docker)

```bash
# 1) установить Docker, если нет
# 2) склонировать репозиторий
git clone https://github.com/ha73r0fa11/fantrax_reminder.git
cd fantrax_reminder

# 3) конфигурация
cp .env.example .env            # вписать TELEGRAM_BOT_TOKEN
cp mapping.example.json mapping.json   # вписать привязку

# 4) запуск
docker compose up -d --build
docker compose logs -f fantrax-bot
```

Для автостарта при перезагрузке сервера `restart: unless-stopped` уже задан в
`docker-compose.yml`.

## Настройка (переменные окружения)

| Переменная | По умолчанию | Описание |
|---|---|---|
| `FANTRAX_LEAGUE_ID` | `rwoc4s02mrui4mac` | ID лиги из URL |
| `TELEGRAM_BOT_TOKEN` | — | токен бота от @BotFather |
| `MAPPING_FILE` | `mapping.json` | путь к файлу привязки (в Docker — `/data/mapping.json`) |
| `POLL_INTERVAL_MINUTES` | `30` | интервал опроса Fantrax |
| `LOG_LEVEL` | `INFO` | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `DRY_RUN` | `false` | `true` — не слать в Telegram, только логировать |
| `STATE_FILE` | `state.json` | путь к файлу состояния (в Docker — `/data/state.json`) |

## Проверка перед запуском

Прогнать в режиме «сухого» запуска и посмотреть, что реально находит бот:

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
  mapping.py      # привязка команда -> chat_id (mapping.json)
  notifier.py     # отправка сообщений в Telegram
  state.py        # дедупликация уведомлений (state.json)
  get_chat_id.py  # утилита: узнать chat_id
  main.py         # основной цикл
```

## Важно

- API Fantrax — **неофициальный**. Его структура может измениться без
  предупреждения; если бот перестал получать данные, проверьте логи.
- Данные лиги должны быть публичными (в этой лиге они отдаются без логина).
- `mapping.json` и `state.json` не попадают в git (см. `.gitignore`).
