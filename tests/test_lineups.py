"""Тесты уведомлений о появлении составов (bot/lineups.py, bot/state.py)."""
import json
import os
import tempfile
import unittest

from bot.lineups import MatchEvent, announced_events
from bot.state import State


def _row(event_id, content, clubs, icons=None, status_id="1"):
    return {
        "statusId": status_id,
        "cells": [{"content": content, "eventId": event_id}],
        "scorer": {
            "scorerId": "p1",
            "teamShortName": clubs[0],
            "teamName": clubs[1],
            "icons": icons or [],
        },
    }


def _roster(rows):
    return {"tables": [{"rows": rows}]}


STARTING = [{"typeId": "12", "tooltip": "Starting in upcoming/current game"}]
BENCH = [{"typeId": "34", "tooltip": "On the bench, potential substitute"}]
EXPECTED = [{"typeId": "32", "tooltip": "Expected to play in upcoming/current game"}]


class AnnouncedEventsTest(unittest.TestCase):
    def test_event_with_lineups_is_reported(self):
        rosters = {
            "t1": _roster(
                [
                    _row("e1", "@ARS<br/>Sat 10:00AM", ("EVE", "Everton"), STARTING),
                    _row("e1", "EVE<br/>Sat 10:00AM", ("ARS", "Arsenal"), BENCH),
                ]
            )
        }
        events = announced_events(rosters)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].event_id, "e1")
        self.assertEqual(events[0].kickoff, "Sat 10:00AM")
        self.assertEqual(events[0].title(), "Arsenal — Everton")

    def test_event_without_lineups_is_skipped(self):
        rosters = {
            "t1": _roster(
                [_row("e2", "@NEW<br/>Sun 9:00AM", ("FUL", "Fulham"), EXPECTED)]
            )
        }
        self.assertEqual(announced_events(rosters), [])

    def test_not_starting_tooltip_counts_as_lineup(self):
        icons = [{"typeId": "99", "tooltip": "Not starting in upcoming/current game"}]
        rosters = {
            "t1": _roster([_row("e3", "@LEE<br/>Sat 7:30AM", ("TOT", "Tottenham"), icons)])
        }
        self.assertEqual([e.event_id for e in announced_events(rosters)], ["e3"])

    def test_reserve_and_injured_slots_are_counted(self):
        # Составы на матч не зависят от того, в каком слоте фэнтези-команды игрок.
        rosters = {
            "t1": _roster(
                [_row("e4", "@BHA<br/>Sun 9:00AM", ("BRF", "Brentford"), STARTING, "2")]
            )
        }
        self.assertEqual([e.event_id for e in announced_events(rosters)], ["e4"])

    def test_rows_without_cells_are_skipped(self):
        rosters = {"t1": _roster([{"statusId": "2", "description": "empty spot"}])}
        self.assertEqual(announced_events(rosters), [])

    def test_title_falls_back_to_short_name(self):
        self.assertEqual(MatchEvent("e5", {"COV": "Coventry City"}).title(), "Coventry City")


class StateLineupEventsTest(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".json")
        os.close(fd)

    def tearDown(self):
        if os.path.exists(self.path):
            os.unlink(self.path)

    def test_events_survive_reload_and_problems_are_kept(self):
        state = State(self.path)
        state.add_lineup_events(["e1", "e2"])
        state.replace_and_save({"t:p": "NOT_STARTING"})

        reloaded = State(self.path)
        self.assertEqual(reloaded.lineup_events, {"e1", "e2"})
        self.assertEqual(reloaded.get("t:p"), "NOT_STARTING")

    def test_missing_file_gives_empty_state(self):
        os.unlink(self.path)
        state = State(self.path)
        self.assertEqual(state.lineup_events, set())
        self.assertEqual(state.notified, {})

    def test_saved_file_shape(self):
        state = State(self.path)
        state.add_lineup_events(["e1"])
        state.replace_and_save({})
        with open(self.path, encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data, {"notified": {}, "lineup_events": ["e1"]})


if __name__ == "__main__":
    unittest.main()
