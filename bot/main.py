"""Точка входа бота.

Режимы:
  python -m bot.main            # цикл: проверка каждые POLL_INTERVAL_MINUTES
  python -m bot.main --once     # одна проверка и выход (удобно для cron)
  python -m bot.main --dry-run  # одна проверка без отправки в Telegram
"""
from __future__ import annotations

import argparse
import logging
import signal
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from .config import load_config
from .fantrax import FantraxClient
from .joins import handle_starts
from .mapping import load_mapping, resolve_chat_ids
from .notifier import send_telegram
from .state import State
from .statuses import PlayerIssue, detect_issues

log = logging.getLogger("fantrax_bot")


def build_message(issues: list[PlayerIssue], checked_at: str) -> str:
    grouped: dict[str, list[PlayerIssue]] = defaultdict(list)
    for issue in issues:
        grouped[issue.team_name].append(issue)

    lines = [f"🚨 Fantrax — риск в основном составе ({checked_at})", ""]
    for team_name in sorted(grouped):
        lines.append(f"{team_name}:")
        for issue in grouped[team_name]:
            lines.append(issue.line())
        lines.append("")
    return "\n".join(lines).rstrip()


def run_once(cfg, client: FantraxClient, state: State) -> int:
    teams = client.teams()
    if not teams:
        log.warning("В лиге не найдено команд.")
        return 0

    # Привязку читаем каждый раз — правки mapping.json подхватываются без рестарта.
    mapping = load_mapping(cfg.mapping_file)
    chat_ids = resolve_chat_ids(mapping, teams)
    if not chat_ids:
        log.warning(
            "В привязке (%s) нет ни одной команды — уведомлять будет некого.",
            cfg.mapping_file,
        )

    log.info("Проверяю составы %d команд", len(teams))
    rosters = client.rosters(list(teams))

    issues: list[PlayerIssue] = []
    for team_id, team_name in teams.items():
        issues.extend(detect_issues(team_id, team_name, rosters[team_id]))

    mapped_issues = [i for i in issues if i.team_id in chat_ids]
    unmapped_teams = sorted(
        {i.team_name for i in issues if i.team_id not in chat_ids}
    )
    if unmapped_teams:
        log.warning(
            "Есть проблемы у команд без привязки (нет chat_id): %s",
            ", ".join(unmapped_teams),
        )

    to_notify = [
        i for i in mapped_issues if state.get(i.key()) != i.severity
    ]

    checked_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    by_chat: dict[str, list[PlayerIssue]] = defaultdict(list)
    for issue in to_notify:
        by_chat[chat_ids[issue.team_id]].append(issue)

    delivered: list[str] = []

    for chat_id, chat_issues in by_chat.items():
        text = build_message(chat_issues, checked_at)
        if cfg.dry_run:
            log.info("[dry-run] В %s было бы отправлено:\n%s", chat_id, text)
            delivered.append(chat_id)
            continue
        try:
            send_telegram(cfg.telegram_bot_token, chat_id, text)
            delivered.append(chat_id)
            log.info(
                "Отправлено уведомление в %s о %d игроках", chat_id, len(chat_issues)
            )
        except Exception as exc:
            # Один недоступный участник не должен блокировать остальных.
            # Его проблемы не помечаем отправленными — повторим в след. цикле.
            log.error("Не удалось отправить в %s: %s", chat_id, exc)

    if to_notify:
        log.info("Всего новых проблем: %d (проблемных игроков: %d)", len(to_notify), len(issues))
    else:
        log.info("Новых проблем нет (проблемных игроков сейчас: %d)", len(issues))

    # Помечаем отправленными только те проблемы, чьё сообщение дошло.
    state.replace_and_save(
        {i.key(): i.severity for i in mapped_issues if chat_ids[i.team_id] in delivered}
    )
    return 0


def next_check_at(
    now: datetime, interval_seconds: int, align_seconds: int
) -> datetime:
    """Ближайшая после ``now`` точка расписания.

    Проверки идут каждые ``interval_seconds`` со сдвигом ``align_seconds``
    от начала часа: для 30 минут и сдвига 20 минут — в :20 и :50.
    """
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elapsed = (now - midnight).total_seconds()
    remainder = (elapsed - align_seconds) % interval_seconds
    return midnight + timedelta(
        seconds=elapsed + interval_seconds - remainder
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Fantrax -> Telegram уведомления")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Одна проверка и выход (без бесконечного цикла)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Не отправлять сообщения в Telegram, только логировать",
    )
    args = parser.parse_args()

    cfg = load_config()
    if args.dry_run:
        cfg.dry_run = True

    logging.basicConfig(
        level=getattr(logging, cfg.log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    if not cfg.dry_run and not cfg.telegram_bot_token:
        log.error(
            "Не задан TELEGRAM_BOT_TOKEN. Заполните .env (см. README) "
            "или запустите с --dry-run."
        )
        return 1

    client = FantraxClient(cfg.league_id)
    state = State(cfg.state_file)

    stop = False

    def _handle_signal(signum, frame):
        nonlocal stop
        log.info("Получен сигнал %s, завершаюсь...", signum)
        stop = True

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    while not stop:
        try:
            run_once(cfg, client, state)
        except Exception as exc:  # не падаем в цикле
            log.exception("Ошибка проверки: %s", exc)

        if not cfg.dry_run:
            try:
                handle_starts(cfg, client)
            except Exception as exc:  # не падаем в цикле
                log.exception("Ошибка обработки новых участников: %s", exc)

        if args.once:
            return 0

        # Проверки привязываем к сетке времени (:20 и :50), а не к моменту
        # запуска — иначе расписание медленно уезжает вперёд.
        target = next_check_at(
            datetime.now(), cfg.poll_interval_seconds, cfg.poll_align_minutes * 60
        )
        log.info("Следующая проверка в %s", target.strftime("%H:%M"))

        # Спим по частям, чтобы быстрее реагировать на сигнал остановки.
        while not stop:
            remaining = (target - datetime.now()).total_seconds()
            if remaining <= 0:
                break
            time.sleep(min(5, remaining))

    return 0


if __name__ == "__main__":
    sys.exit(main())
