from __future__ import annotations

import unittest
from urllib.parse import parse_qs, urlparse

from backend.app.gameplay_config import (
    GAME_CONFIG,
    calculate_win_score,
    chapter_and_level_for_round,
    mission_for_round,
)
from backend.app.service import GameService, SESSION_TTL_SECONDS
from backend.app.trajectory_store import TrajectoryStore


class FakeClock:
    def __init__(self, start: float = 1_000.0) -> None:
        self.current = start

    def __call__(self) -> float:
        return self.current

    def advance(self, seconds: float) -> None:
        self.current += seconds


class GameServiceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.trajectory_store = TrajectoryStore()

    def setUp(self) -> None:
        self.clock = FakeClock()
        self.service = GameService(
            trajectory_store=self.trajectory_store,
            clock=self.clock,
        )

    def test_start_session_accepts_missing_player_id(self) -> None:
        snapshot = self.service.start_session(None)

        session = self.service.sessions[snapshot.session_id]
        self.assertEqual(session.player_id, "anonymous")
        self.assertEqual(snapshot.frames_remaining, session.frames_remaining)
        self.assertGreater(snapshot.seconds_remaining, 0)

    def test_start_session_uses_round_configuration(self) -> None:
        snapshot = self.service.start_session("player-a")
        mission = mission_for_round(1)
        chapter, level = chapter_and_level_for_round(1)

        self.assertEqual(snapshot.chapter, chapter)
        self.assertEqual(snapshot.level, level)
        self.assertEqual(snapshot.mission_title, mission.title)
        self.assertEqual(snapshot.stability, GAME_CONFIG.initial_session.stability)
        self.assertEqual(snapshot.corruption, GAME_CONFIG.initial_session.corruption)

    def test_render_frame_returns_offline_manifest_svg(self) -> None:
        snapshot = self.service.start_session("player-a")
        session = self.service.sessions[snapshot.session_id]
        query = parse_qs(urlparse(snapshot.image_url).query)
        variant_key = query["variant"][0]
        token = query["token"][0]

        svg = self.service.render_frame(
            snapshot.session_id,
            snapshot.frame_index,
            variant_key,
            token,
        )

        expected_svg = self.trajectory_store.get_frame_svg(
            target_label=session.target.label,
            variant_key=variant_key,
            frame_index=snapshot.frame_index,
        )
        self.assertEqual(svg, expected_svg)

    def test_sessions_are_scoped_to_player_id(self) -> None:
        snapshot = self.service.start_session("player-a")

        with self.assertRaises(KeyError):
            self.service.step("player-b", snapshot.session_id)

    def test_expired_session_is_pruned(self) -> None:
        snapshot = self.service.start_session("player-a")

        self.clock.advance(SESSION_TTL_SECONDS + 1)

        with self.assertRaises(KeyError):
            self.service.step("player-a", snapshot.session_id)

    def test_correct_guess_uses_configured_scoring(self) -> None:
        snapshot = self.service.start_session("player-a")
        session = self.service.sessions[snapshot.session_id]

        result = self.service.guess("player-a", snapshot.session_id, session.target.label)

        expected_score = calculate_win_score(
            session.mission_type,
            progress=0,
            frames_remaining=snapshot.frames_remaining,
            stability=snapshot.stability,
            corruption=snapshot.corruption,
            cards_remaining=snapshot.cards_remaining,
            freeze_available=snapshot.freeze_available,
            scan_charges=snapshot.scan_charges,
            remaining_guesses=snapshot.remaining_guesses,
        )
        self.assertEqual(result.score, expected_score)
        self.assertEqual(result.status, "won")


class TrajectoryStoreTest(unittest.TestCase):
    def test_get_frame_svg_decodes_manifest_data_uri(self) -> None:
        store = TrajectoryStore()
        target_label = store.target_labels[0]

        encoded_frame = store.get_frame(target_label, "base", 0)
        decoded_frame = store.get_frame_svg(target_label, "base", 0)

        self.assertTrue(encoded_frame.startswith("data:image/svg+xml;utf8,"))
        self.assertTrue(decoded_frame.startswith("<svg"))


if __name__ == "__main__":
    unittest.main()
