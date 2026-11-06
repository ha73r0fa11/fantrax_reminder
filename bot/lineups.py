"""Появление составов на матч.

Fantrax отдаёт по каждому игроку ``eventId`` его матча и ячейку с соперником
и временем начала (``cells[0]``: ``@ARS<br/>Sat 10:00AM``). Как только у
любого игрока матча появляется иконка состава — «Starting», «On the bench»
или «Not starting», — считаем, что составы на этот матч объявлены.

Видны только матчи, в которых играет хотя бы один игрок из составов лиги:
других игроков API не отдаёт.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Fantrax отдаёт время матчей по US Eastern, а получатели — в Москве.
SOURCE_TZ = ZoneInfo("America/New_York")
DISPLAY_TZ = ZoneInfo("Europe/Moscow")

_WEEKDAYS_EN = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}
_WEEKDAYS_RU = (
    "понедельник",
    "вторник",
    "среда",
    "четверг",
    "пятница",
    "суббота",
    "воскресенье",
)
_KICKOFF_RE = re.compile(r"^([A-Za-z]{3})\s+(\d{1,2}):(\d{2})\s*([AP]M)$")

# «Starting in upcoming/current game» и «On the bench, potential substitute».
LINEUP_TYPE_IDS = frozenset({"12", "34"})
LINEUP_TOOLTIP_PREFIXES = (
    "starting in upcoming",
    "not starting",
    "on the bench",
)


@dataclass
class MatchEvent:
    event_id: str
    clubs: dict[str, str] = field(default_factory=dict)  # короткое имя -> полное
    kickoff: str = ""

    def title(self) -> str:
        return " — ".join(
            self.clubs.get(short, short) for short in sorted(self.clubs)
        )


def _has_lineup(icons: list[dict] | None) -> bool:
    for icon in icons or []:
        if str(icon.get("typeId")) in LINEUP_TYPE_IDS:
            return True
        tooltip = str(icon.get("tooltip") or "").lower()
        if any(tooltip.startswith(prefix) for prefix in LINEUP_TOOLTIP_PREFIXES):
            return True
    return False


def _kickoff(content: object) -> str:
    """Время из ячейки соперника: ``@ARS<br/>Sat 10:00AM`` -> ``Sat 10:00AM``."""
    parts = str(content or "").split("<br/>")
    return parts[-1].strip() if len(parts) > 1 else ""


def kickoff_msk(kickoff: str, now: datetime) -> str:
    """«Fri 3:00PM» (US Eastern) -> «пятница, 23:00 МСК».

    В строке нет даты, только день недели, поэтому берём ближайший такой
    день — от него зависит переход на летнее время и, значит, сдвиг часа.
    """
    match = _KICKOFF_RE.match(kickoff.strip())
    if not match:
        return ""
    weekday = _WEEKDAYS_EN.get(match.group(1).lower())
    if weekday is None:
        return ""

    hour = int(match.group(2)) % 12
    if match.group(4).upper() == "PM":
        hour += 12

    today = now.astimezone(SOURCE_TZ).date()
    day = today + timedelta(days=(weekday - today.weekday()) % 7)
    local = datetime(
        day.year, day.month, day.day, hour, int(match.group(3)), tzinfo=SOURCE_TZ
    )
    msk = local.astimezone(DISPLAY_TZ)
    return f"{_WEEKDAYS_RU[msk.weekday()]}, {msk:%H:%M} МСК"


def announced_events(rosters: dict[str, dict]) -> list[MatchEvent]:
    """Матчи, по которым уже опубликованы составы."""
    events: dict[str, MatchEvent] = {}
    ready: set[str] = set()

    for roster in rosters.values():
        for table in roster.get("tables", []):
            for row in table.get("rows", []):
                scorer = row.get("scorer") or {}
                cells = row.get("cells") or []
                if not scorer or not cells:
                    continue

                event_id = str(cells[0].get("eventId") or "")
                if not event_id:
                    continue

                event = events.setdefault(event_id, MatchEvent(event_id))
                short = str(scorer.get("teamShortName") or scorer.get("teamName") or "?")
                event.clubs.setdefault(short, str(scorer.get("teamName") or short))
                if not event.kickoff:
                    event.kickoff = _kickoff(cells[0].get("content"))
                if _has_lineup(scorer.get("icons")):
                    ready.add(event_id)

    return [event for event_id, event in events.items() if event_id in ready]
