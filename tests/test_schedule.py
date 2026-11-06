"""Тесты расписания проверок (bot/main.py: next_check_at)."""
import unittest
from datetime import datetime

from bot.main import next_check_at

HALF_HOUR = 1800
ALIGN_20_MIN = 20 * 60


def _at(hour, minute, second=0):
    return datetime(2026, 11, 6, hour, minute, second)


class NextCheckAtTest(unittest.TestCase):
    def test_round_hour_is_push_to_20(self):
        self.assertEqual(next_check_at(_at(10, 0), HALF_HOUR, ALIGN_20_MIN), _at(10, 20))

    def test_just_after_slot_goes_to_next_slot(self):
        self.assertEqual(
            next_check_at(_at(10, 20, 5), HALF_HOUR, ALIGN_20_MIN), _at(10, 50)
        )

    def test_second_slot_rolls_over_to_next_hour(self):
        self.assertEqual(next_check_at(_at(10, 50), HALF_HOUR, ALIGN_20_MIN), _at(11, 20))

    def test_midnight_rollover(self):
        self.assertEqual(
            next_check_at(datetime(2026, 11, 6, 23, 55), HALF_HOUR, ALIGN_20_MIN),
            datetime(2026, 11, 7, 0, 20),
        )

    def test_hourly_interval_with_same_alignment(self):
        self.assertEqual(
            next_check_at(_at(10, 0), 3600, ALIGN_20_MIN), _at(10, 20)
        )
        self.assertEqual(
            next_check_at(_at(10, 25), 3600, ALIGN_20_MIN), _at(11, 20)
        )

    def test_result_is_always_in_the_future(self):
        now = _at(10, 20)
        self.assertGreater(next_check_at(now, HALF_HOUR, ALIGN_20_MIN), now)


if __name__ == "__main__":
    unittest.main()
