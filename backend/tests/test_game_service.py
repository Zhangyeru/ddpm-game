from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import parse_qs, urlparse

from backend.app.auth import SQLiteAuthStore, actor_id_for_user
from backend.app.gameplay_config import (
    GAME_CONFIG,
    calculate_loss_breakdown,
    calculate_score_breakdown,
    first_level,
    level_by_id,
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

    def test_start_session_uses_current_level_configuration(self) -> None:
        snapshot = self.service.start_session("player-a")
        level = first_level()

        self.assertEqual(snapshot.level_id, level.level_id)
        self.assertEqual(snapshot.chapter_title, level.chapter_title)
        self.assertEqual(snapshot.level_title, level.level_title)
        self.assertEqual(snapshot.level_summary, level.summary)
        self.assertEqual(snapshot.mission_title, level.mission_title)
        self.assertEqual(snapshot.stability, level.initial_stability)
        self.assertEqual(snapshot.corruption, level.initial_corruption)
        self.assertEqual(snapshot.remaining_guesses, level.max_guesses)
        self.assertEqual(snapshot.cards_remaining, level.max_cards)

    def test_progression_defaults_to_first_level(self) -> None:
        progression = self.service.get_progression("player-a")

        self.assertEqual(progression.current_level_id, "chapter-1-level-1")
        self.assertEqual(progression.highest_unlocked_level_id, "chapter-1-level-1")
        self.assertEqual(progression.completed_count, 0)
        self.assertFalse(progression.campaign_complete)
        self.assertTrue(progression.current_level.is_current)

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
            max_cards_total=session.max_cards,
            process_score_total=0,
        )
        self.assertEqual(result.score, expected_breakdown.final_score)
        self.assertEqual(result.status, "won")
        self.assertIsNotNone(result.score_breakdown)
        self.assertEqual(result.score_breakdown.final_score, expected_breakdown.final_score)
        self.assertEqual(result.score_breakdown.settlement_score, expected_breakdown.settlement_score)
        self.assertEqual(result.score_events[-1].kind, "settlement")
        self.assertEqual(result.score_events[-1].delta, expected_breakdown.settlement_score)
        self.assertTrue(result.awaiting_advancement)
        self.assertEqual(result.next_level_id, "chapter-1-level-2")
        self.assertIsNotNone(result.ended_at)

    def test_advance_unlocks_and_starts_next_level(self) -> None:
        snapshot = self.service.start_session("player-a")
        session = self.service.sessions[snapshot.session_id]
        won = self.service.guess("player-a", snapshot.session_id, session.target.label)

        next_session = self.service.advance("player-a", won.session_id)
        progression = self.service.get_progression("player-a")

        self.assertEqual(next_session.level_id, "chapter-1-level-2")
        self.assertEqual(next_session.status, "playing")
        self.assertEqual(progression.current_level_id, "chapter-1-level-2")
        self.assertEqual(progression.highest_unlocked_level_id, "chapter-1-level-2")
        self.assertIn("chapter-1-level-1", progression.completed_level_ids)

    def test_loss_does_not_advance_level(self) -> None:
        snapshot = self.service.start_session("player-a")
        session = self.service.sessions[snapshot.session_id]
        wrong_label = next(
            label for label in snapshot.candidate_labels if label != session.target.label
        )

        for _ in range(session.max_guesses):
            result = self.service.guess("player-a", snapshot.session_id, wrong_label)

        progression = self.service.get_progression("player-a")

        self.assertEqual(result.status, "lost")
        self.assertEqual(progression.current_level_id, "chapter-1-level-1")
        self.assertEqual(progression.highest_unlocked_level_id, "chapter-1-level-1")
        self.assertEqual(progression.completed_count, 0)

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

        for _ in range(session.max_guesses):
            result = self.service.guess("player-a", snapshot.session_id, wrong_label)

        expected_process_score = GAME_CONFIG.actions.wrong_guess.score * session.max_guesses
        expected_breakdown = calculate_loss_breakdown(process_score_total=expected_process_score)

        self.assertEqual(result.status, "lost")
        self.assertEqual(result.loss_reason, "猜测次数耗尽。")
        self.assertIsNotNone(result.score_breakdown)
        self.assertEqual(result.score_breakdown.final_score, expected_breakdown.final_score)
        self.assertEqual(result.score_events[-1].kind, "loss")
        self.assertEqual(result.score_events[-1].delta, 0)
        self.assertFalse(result.awaiting_advancement)
        self.assertIsNotNone(result.ended_at)

    def test_sample_selection_stays_stable_within_session(self) -> None:
        snapshot = self.service.start_session("player-a")
        session = self.service.sessions[snapshot.session_id]
        initial_sample_id = session.sample_id

        self.service.step("player-a", snapshot.session_id)
        self.service.use_card("player-a", snapshot.session_id, "sharpen-outline")

        self.assertEqual(self.service.sessions[snapshot.session_id].sample_id, initial_sample_id)

    def test_final_level_win_marks_campaign_complete(self) -> None:
        progress = self.service._campaign_progress("player-a")
        progress.current_level_id = "chapter-4-level-3"
        progress.highest_unlocked_level_id = "chapter-4-level-3"
        progress.completed_level_ids = {
            level.level_id for level in map(level_by_id, [
                "chapter-1-level-1",
                "chapter-1-level-2",
                "chapter-1-level-3",
                "chapter-2-level-1",
                "chapter-2-level-2",
                "chapter-2-level-3",
                "chapter-3-level-1",
                "chapter-3-level-2",
                "chapter-3-level-3",
                "chapter-4-level-1",
                "chapter-4-level-2",
            ])
        }
        snapshot = self.service.start_current_level("player-a")
        session = self.service.sessions[snapshot.session_id]

        result = self.service.guess("player-a", snapshot.session_id, session.target.label)
        progression = self.service.get_progression("player-a")

        self.assertEqual(result.status, "won")
        self.assertTrue(result.campaign_complete)
        self.assertFalse(result.awaiting_advancement)
        self.assertIsNone(result.next_level_id)
        self.assertTrue(progression.campaign_complete)
        self.assertEqual(progression.current_level_id, "chapter-1-level-1")
        self.assertEqual(progression.completed_count, 12)

    def test_authenticated_progress_persists_in_sqlite_store(self) -> None:
        with TemporaryDirectory() as temp_dir:
            auth_store = SQLiteAuthStore(Path(temp_dir) / "auth.sqlite3")
            user = auth_store.create_user("tester_01", "hashed-password")
            actor_id = actor_id_for_user(user.id)
            service = GameService(
                trajectory_store=self.trajectory_store,
                auth_store=auth_store,
                clock=self.clock,
            )

            snapshot = service.start_current_level(actor_id)
            session = service.sessions[snapshot.session_id]
            won = service.guess(actor_id, snapshot.session_id, session.target.label)
            service.advance(actor_id, won.session_id)

            persisted_progress = auth_store.get_or_create_progress(user.id)
            self.assertEqual(persisted_progress.current_level_id, "chapter-1-level-2")
            self.assertEqual(
                persisted_progress.highest_unlocked_level_id,
                "chapter-1-level-2",
            )
            self.assertIn("chapter-1-level-1", persisted_progress.completed_level_ids)

            next_service = GameService(
                trajectory_store=self.trajectory_store,
                auth_store=auth_store,
                clock=self.clock,
            )
            progression = next_service.get_progression(actor_id)
            self.assertEqual(progression.current_level_id, "chapter-1-level-2")


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
