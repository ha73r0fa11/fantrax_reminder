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
| On the bench, potential substitute | `typeId=34` | не в старте, в лучшем случае выйдет на замену |
| Not starting in upcoming/current game | по тексту подсказки | объявлен состав, игрока в нём нет |
| Late fitness test / Game-time decision | `typeId=1` | под вопросом, может не выйти со старта |

Статусы «Starting in upcoming/current game» (`typeId=12`) и «Expected to
play in upcoming/current game» (`typeId=32`) означают, что с игроком всё в
порядке, — они игнорируются, как и остальные статусы. Иконки состава
появляются примерно за час до начала матча. Правила лежат в
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

Telegram разрешает боту писать только тем, кто уже запускал бота, поэтому
каждый участник один раз нажимает «Старт» у бота — после этого chat_id
собирается автоматически по списку `@username`.

1. Создайте `participants.json` по образцу `participants.example.json`:

   ```json
   {
     "Fq": "@username1",
     "butep": "@username2"
   }
   ```

2. Попросите всех участников нажать «Старт» у бота (отправить ему любое
   сообщение).

3. Соберите `mapping.json` автоматически:

   ```bash
   python -m bot.link
   ```

   Скрипт запишет `mapping.json` (команда -> chat_id) и перечислит тех, кто
   ещё не нажал «Старт». Запускать можно сколько угодно раз, в любом
   порядке: уже собранные привязки сохраняются, добавляются только новые.

Если chat_id известны заранее, привязку можно вписать в `mapping.json`
вручную (ключ — название команды или её ID):

   ```json
   {
     "Fq": 123456789,
     "butep": 987654321
   }
   ```

Проверить команды и текущую привязку: `python -m bot.mapping`.

**Подключать участников можно постепенно.** Уведомления получают только
привязанные команды; команды без `chat_id` просто пропускаются (в логе будет
предупреждение с их списком). Недоступный получатель (заблокировал бота) тоже
не мешает остальным: ошибка пишется в лог, отправка ему повторится в
следующем цикле.

## Быстрый старт (Docker)

1. `cp .env.example .env` и впишите `TELEGRAM_BOT_TOKEN` (от
   [@BotFather](https://t.me/BotFather)).
2. `mkdir -p data` — здесь будут `state.json`, `mapping.json` и
   `participants.json`.
3. `cp participants.example.json data/participants.json` и впишите @username
   участников.
4. Запустите:

   ```bash
   docker compose up -d --build
   ```

   Логи: `docker compose logs -f fantrax-bot`.

5. После того как участники нажмут «Старт», создайте привязку:

   ```bash
   docker compose run --rm fantrax-bot python -m bot.link
   ```

`mapping.json` перечитывается на каждой проверке, поэтому правки привязки
подхватываются без перезапуска.

## Запуск без Docker

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate ; Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # впишите токен
cp participants.example.json participants.json  # @username участников
python -m bot.get_chat_id     # посмотреть, кто уже запустил бота
python -m bot.link            # собрать mapping.json
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
mkdir -p data
cp participants.example.json data/participants.json   # @username участников

# 4) запуск
docker compose up -d --build
docker compose logs -f fantrax-bot

# 5) после того как участники нажмут «Старт» — собрать привязку
docker compose run --rm fantrax-bot python -m bot.link
```

Для автостарта при перезагрузке сервера `restart: unless-stopped` уже задан в
`docker-compose.yml`.

## Настройка (переменные окружения)

| Переменная | По умолчанию | Описание |
|---|---|---|
| `FANTRAX_LEAGUE_ID` | `rwoc4s02mrui4mac` | ID лиги из URL |
| `TELEGRAM_BOT_TOKEN` | — | токен бота от @BotFather |
| `MAPPING_FILE` | `mapping.json` | путь к файлу привязки (в Docker — `/data/mapping.json`) |
| `PARTICIPANTS_FILE` | `participants.json` | список участников для `bot.link` (в Docker — `/data/participants.json`) |
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
  link.py         # сбор chat_id по @username -> mapping.json
  notifier.py     # отправка сообщений в Telegram
  state.py        # дедупликация уведомлений (state.json)
  get_chat_id.py  # утилита: узнать chat_id
  main.py         # основной цикл
```

## Важно

- API Fantrax — **неофициальный**. Его структура может измениться без
  предупреждения; если бот перестал получать данные, проверьте логи.
- Данные лиги должны быть публичными (в этой лиге они отдаются без логина).
- `.env`, `data/mapping.json`, `data/participants.json` и `data/state.json`
  не попадают в git (см. `.gitignore`).
