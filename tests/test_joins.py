"""Тесты привязки новых участников (bot/joins.py)."""
import unittest

from bot.joins import apply_chats, message_chats

TEAMS = {"t1": "rrk", "t2": "BigSummer"}
PARTICIPANTS = {"rrk": "@alt_t0t", "BigSummer": "@TheFriendofKUTs"}


def _chat(chat_id, username=None):
    chat = {"id": chat_id}
    if username is not None:
        chat["username"] = username
    return chat


class ApplyChatsTest(unittest.TestCase):
    def test_new_participant_is_linked(self):
        mapping = {}
        messages, changed = apply_chats(
            [_chat(777, "alt_t0t")], mapping, PARTICIPANTS, TEAMS
        )
        self.assertTrue(changed)
        self.assertEqual(mapping, {"rrk": "777"})
        self.assertEqual(len(messages), 1)
        self.assertIn("@alt_t0t", messages[0])
        self.assertIn("rrk", messages[0])

    def test_participants_username_with_at_sign_and_case(self):
        participants = {"rrk": "@Alt_T0T"}
        mapping = {}
        apply_chats([_chat(777, "alt_t0t")], mapping, participants, TEAMS)
        self.assertEqual(mapping, {"rrk": "777"})

    def test_already_linked_is_silent(self):
        mapping = {"rrk": "777"}
        messages, changed = apply_chats(
            [_chat(777, "alt_t0t")], mapping, PARTICIPANTS, TEAMS
        )
        self.assertEqual(messages, [])
        self.assertFalse(changed)

    def test_new_chat_id_relinks(self):
        mapping = {"rrk": "111"}
        messages, changed = apply_chats(
            [_chat(777, "alt_t0t")], mapping, PARTICIPANTS, TEAMS
        )
        self.assertTrue(changed)
        self.assertEqual(mapping, {"rrk": "777"})
        self.assertEqual(len(messages), 1)

    def test_unknown_username_is_reported_but_not_linked(self):
        mapping = {}
        messages, changed = apply_chats(
            [_chat(777, "stranger")], mapping, PARTICIPANTS, TEAMS
        )
        self.assertFalse(changed)
        self.assertEqual(mapping, {})
        self.assertIn("participants.json", messages[0])

    def test_wrong_team_name_is_reported(self):
        participants = {"Нет такой": "@alt_t0t"}
        mapping = {}
        messages, changed = apply_chats(
            [_chat(777, "alt_t0t")], mapping, participants, TEAMS
        )
        self.assertFalse(changed)
        self.assertEqual(mapping, {})
        self.assertIn("не найдена в лиге", messages[0])

    def test_chat_without_username(self):
        mapping = {}
        messages, changed = apply_chats(
            [_chat(777)], mapping, PARTICIPANTS, TEAMS
        )
        self.assertFalse(changed)
        self.assertIn("без @username", messages[0])


class MessageChatsTest(unittest.TestCase):
    def test_extracts_chats_from_updates(self):
        updates = [
            {"update_id": 1, "message": {"chat": {"id": 5, "username": "a"}}},
            {"update_id": 2, "edited_message": {"chat": {"id": 6}}},
            {"update_id": 3, "message": {}},
        ]
        self.assertEqual(message_chats(updates), [{"id": 5, "username": "a"}])


if __name__ == "__main__":
    unittest.main()
