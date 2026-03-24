from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import parse_qs, urlparse

from backend.app.gameplay_config import (
    GAME_CONFIG,
    calculate_loss_breakdown,
    calculate_score_breakdown,
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

    def test_render_frame_returns_offline_manifest_asset(self) -> None:
        snapshot = self.service.start_session("player-a")
        session = self.service.sessions[snapshot.session_id]
        query = parse_qs(urlparse(snapshot.image_url).query)
        variant_key = query["variant"][0]
        token = query["token"][0]

        asset = self.service.render_frame(
            snapshot.session_id,
            snapshot.frame_index,
            variant_key,
            token,
        )

        expected_asset = self.trajectory_store.get_frame(
            target_label=session.target.label,
            sample_id=session.sample_id,
            variant_key=variant_key,
            frame_index=snapshot.frame_index,
        )
        self.assertEqual(asset.path, expected_asset.path)
        self.assertEqual(asset.media_type, "image/webp")

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

        expected_breakdown = calculate_score_breakdown(
            session.mission_type,
            progress=0,
            frames_remaining=snapshot.frames_remaining,
            total_frames=snapshot.total_frames,
            stability=snapshot.stability,
            corruption=snapshot.corruption,
            cards_remaining=snapshot.cards_remaining,
            process_score_total=0,
        )
        self.assertEqual(result.score, expected_breakdown.final_score)
        self.assertEqual(result.status, "won")
        self.assertIsNotNone(result.score_breakdown)
        self.assertEqual(result.score_breakdown.final_score, expected_breakdown.final_score)
        self.assertEqual(result.score_breakdown.settlement_score, expected_breakdown.settlement_score)
        self.assertEqual(result.score_events[-1].kind, "settlement")
        self.assertEqual(result.score_events[-1].delta, expected_breakdown.settlement_score)
        self.assertIsNotNone(result.ended_at)

    def test_card_usage_appends_score_event(self) -> None:
        snapshot = self.service.start_session("player-a")

        result = self.service.use_card("player-a", snapshot.session_id, "sharpen-outline")

        self.assertEqual(result.score, GAME_CONFIG.actions.sharpen_outline.score)
        self.assertEqual(len(result.score_events), 1)
        self.assertEqual(result.score_events[0].kind, "card")
        self.assertEqual(result.score_events[0].title, "轮廓锐化")
        self.assertEqual(result.score_events[0].delta, GAME_CONFIG.actions.sharpen_outline.score)
        self.assertEqual(result.score_events[0].running_score, result.score)

    def test_wrong_guess_appends_penalty_event(self) -> None:
        snapshot = self.service.start_session("player-a")
        session = self.service.sessions[snapshot.session_id]
        wrong_label = next(
            label for label in snapshot.candidate_labels if label != session.target.label
        )

        result = self.service.guess("player-a", snapshot.session_id, wrong_label)

        self.assertEqual(result.score, GAME_CONFIG.actions.wrong_guess.score)
        self.assertEqual(result.score_events[-1].kind, "guess_penalty")
        self.assertEqual(result.score_events[-1].delta, GAME_CONFIG.actions.wrong_guess.score)
        self.assertIn(wrong_label, result.score_events[-1].detail)

    def test_loss_snapshot_includes_reason_and_score_history(self) -> None:
        snapshot = self.service.start_session("player-a")
        session = self.service.sessions[snapshot.session_id]
        wrong_label = next(
            label for label in snapshot.candidate_labels if label != session.target.label
        )

        for _ in range(GAME_CONFIG.resources.max_guesses):
            result = self.service.guess("player-a", snapshot.session_id, wrong_label)

        expected_process_score = GAME_CONFIG.actions.wrong_guess.score * GAME_CONFIG.resources.max_guesses
        expected_breakdown = calculate_loss_breakdown(process_score_total=expected_process_score)

        self.assertEqual(result.status, "lost")
        self.assertEqual(result.loss_reason, "猜测次数耗尽。")
        self.assertIsNotNone(result.score_breakdown)
        self.assertEqual(result.score_breakdown.final_score, expected_breakdown.final_score)
        self.assertEqual(result.score_events[-1].kind, "loss")
        self.assertEqual(result.score_events[-1].delta, 0)
        self.assertIsNotNone(result.ended_at)

    def test_sample_selection_stays_stable_within_session(self) -> None:
        snapshot = self.service.start_session("player-a")
        session = self.service.sessions[snapshot.session_id]
        initial_sample_id = session.sample_id

        self.service.step("player-a", snapshot.session_id)
        self.service.use_card("player-a", snapshot.session_id, "sharpen-outline")

        self.assertEqual(self.service.sessions[snapshot.session_id].sample_id, initial_sample_id)


class TrajectoryStoreTest(unittest.TestCase):
    def test_get_frame_returns_binary_asset_metadata(self) -> None:
        store = TrajectoryStore()
        target_label = store.target_labels[0]
        sample_id = store.sample_ids_for_target(target_label)[0]

        asset = store.get_frame(target_label, sample_id, "base", 0)
        content = asset.read_bytes()

        self.assertTrue(asset.path.exists())
        self.assertEqual(asset.media_type, "image/webp")
        self.assertEqual(content[:4], b"RIFF")
        self.assertEqual(content[8:12], b"WEBP")

    def test_version_3_manifest_preserves_generator_metadata(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            asset_path = root / "generated" / "cat" / "sample-01" / "base" / "000.webp"
            asset_path.parent.mkdir(parents=True)
            asset_path.write_bytes(b"RIFF0000WEBP")
            manifest_path = root / "manifest.json"
            manifest_path.write_text(
                """
                {
                  "version": 3,
                  "total_frames": 100,
                  "variant_keys": ["base"],
                  "generator": {
                    "model_id": "hf-internal-testing/tiny-stable-diffusion-pipe",
                    "scheduler": "ddim_inversion",
                    "num_steps": 100,
                    "device_mode": "cpu"
                  },
                  "targets": {
                    "猫": {
                      "samples": {
                        "sample-01": {
                          "variants": {
                            "base": ["generated/cat/sample-01/base/000.webp"]
                          }
                        }
                      }
                    }
                  }
                }
                """.strip(),
                encoding="utf-8",
            )

            store = TrajectoryStore(manifest_path)

            self.assertEqual(store.version, 3)
            self.assertEqual(store.generator_metadata["scheduler"], "ddim_inversion")


if __name__ == "__main__":
    unittest.main()
