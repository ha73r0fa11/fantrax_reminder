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
from datetime import datetime, timezone

from .config import load_config
from .fantrax import FantraxClient
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

    log.info("Проверяю составы %d команд", len(teams))
    rosters = client.rosters(list(teams))

    issues: list[PlayerIssue] = []
    for team_id, team_name in teams.items():
        issues.extend(detect_issues(team_id, team_name, rosters[team_id]))

    current = {issue.key(): issue.severity for issue in issues}
    to_notify = [
        issue for issue in issues if state.get(issue.key()) != issue.severity
    ]

    if to_notify:
        checked_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        text = build_message(to_notify, checked_at)
        if cfg.dry_run:
            log.info("[dry-run] Было бы отправлено:\n%s", text)
        else:
            send_telegram(cfg.telegram_bot_token, cfg.telegram_chat_id, text)
            log.info(
                "Отправлено уведомление о %d игроках (всего проблемных: %d)",
                len(to_notify),
                len(issues),
            )
    else:
        log.info("Новых проблем нет (проблемных игроков сейчас: %d)", len(issues))

    state.replace_and_save(current)
    return 0


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

    if not cfg.dry_run and (not cfg.telegram_bot_token or not cfg.telegram_chat_id):
        log.error(
            "Не заданы TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID. "
            "Заполните .env (см. README) или запустите с --dry-run."
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

        if args.once:
            return 0

        # Спим по частям, чтобы быстрее реагировать на сигнал остановки.
        waited = 0
        while waited < cfg.poll_interval_seconds and not stop:
            time.sleep(min(5, cfg.poll_interval_seconds - waited))
            waited += 5

    return 0


if __name__ == "__main__":
    sys.exit(main())
