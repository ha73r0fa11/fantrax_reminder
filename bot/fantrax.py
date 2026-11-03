"""Тонкий HTTP-клиент к неофициальному API Fantrax.

Fantrax отдаёт данные по POST-запросу на https://www.fantrax.com/fxpa/req
с телом {"msgs": [{"method": "...", "data": {"leagueId": "...", ...}}]}.
Один запрос может нести несколько method-вызовов (батчинг) — этим мы
пользуемся, чтобы получить составы всех команд одной операцией.
"""
from __future__ import annotations

import logging
from typing import Any

import requests

log = logging.getLogger("fantrax_bot")

API_URL = "https://www.fantrax.com/fxpa/req"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


class FantraxError(RuntimeError):
    """Ошибка взаимодействия с API Fantrax."""


class FantraxClient:
    def __init__(self, league_id: str, timeout: int = 30) -> None:
        self.league_id = league_id
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Content-Type": "application/json",
            }
        )

    def _call(self, methods: list[dict[str, Any]]) -> list[dict[str, Any]]:
        msgs = []
        for method in methods:
            data: dict[str, Any] = {"leagueId": self.league_id}
            data.update(method.get("data", {}))
            msgs.append({"method": method["method"], "data": data})

        resp = self.session.post(
            API_URL,
            params={"leagueId": self.league_id},
            json={"msgs": msgs},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        payload = resp.json()

        if "pageError" in payload:
            err = payload.get("pageError", {})
            raise FantraxError(
                f"Fantrax вернул ошибку: code={err.get('code')} "
                f"title={err.get('title')}"
            )
        if "responses" not in payload:
            raise FantraxError(
                f"Неожиданный ответ Fantrax: {sorted(payload.keys())}"
            )

        return [r["data"] for r in payload["responses"]]

    def teams(self) -> dict[str, str]:
        """Возвращает {team_id: имя_команды} для всех команд лиги."""
        data = self._call(
            [{"method": "getStandings", "data": {"view": "OVERALL"}}]
        )[0]
        return {
            team_id: team.get("name", team_id)
            for team_id, team in data.get("fantasyTeamInfo", {}).items()
        }

    def rosters(self, team_ids: list[str]) -> dict[str, dict[str, Any]]:
        """Возвращает {team_id: ответ getTeamRosterInfo(view=STATS)}.

        Все команды запрашиваются одним пакетным POST-запросом.
        """
        methods = [
            {
                "method": "getTeamRosterInfo",
                "data": {"teamId": team_id, "view": "STATS"},
            }
            for team_id in team_ids
        ]
        responses = self._call(methods)
        return dict(zip(team_ids, responses))
