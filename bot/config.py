"""Конфигурация бота из переменных окружения (или файла .env)."""
from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

DEFAULT_LEAGUE_ID = "rwoc4s02mrui4mac"
DEFAULT_POLL_INTERVAL_MINUTES = 30


def _as_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Config:
    league_id: str
    telegram_bot_token: str
    mapping_file: str
    participants_file: str
    poll_interval_seconds: int
    state_file: str
    dry_run: bool
    log_level: str


def load_config() -> Config:
    poll_minutes = int(
        os.environ.get("POLL_INTERVAL_MINUTES", DEFAULT_POLL_INTERVAL_MINUTES)
    )
    return Config(
        league_id=os.environ.get("FANTRAX_LEAGUE_ID", DEFAULT_LEAGUE_ID),
        telegram_bot_token=os.environ.get("TELEGRAM_BOT_TOKEN", ""),
        mapping_file=os.environ.get("MAPPING_FILE", "mapping.json"),
        participants_file=os.environ.get("PARTICIPANTS_FILE", "participants.json"),
        poll_interval_seconds=max(10, poll_minutes * 60),
        state_file=os.environ.get("STATE_FILE", "state.json"),
        dry_run=_as_bool(os.environ.get("DRY_RUN", "false")),
        log_level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    )
