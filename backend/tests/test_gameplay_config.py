from __future__ import annotations

import unittest

from backend.app.gameplay_config import (
    GAME_CONFIG,
    calculate_win_score,
    card_effect,
    chapter_and_level_for_round,
    mission_for_round,
    phase_label,
    threat_label,
)


class GameplayConfigTest(unittest.TestCase):
    def test_round_structure_follows_config(self) -> None:
        self.assertEqual(chapter_and_level_for_round(1), (1, 1))
        self.assertEqual(chapter_and_level_for_round(8), (1, 8))
        self.assertEqual(chapter_and_level_for_round(9), (2, 1))
        self.assertEqual(chapter_and_level_for_round(24), (3, 8))
        self.assertEqual(chapter_and_level_for_round(25), (3, 1))

    def test_mission_cycle_repeats(self) -> None:
        self.assertEqual(mission_for_round(1).mission_type, "speed")
        self.assertEqual(mission_for_round(2).mission_type, "stability")
        self.assertEqual(mission_for_round(3).mission_type, "precision")
        self.assertEqual(mission_for_round(4).mission_type, "speed")

    def test_calculate_win_score_uses_default_tuning(self) -> None:
        score = calculate_win_score(
            "speed",
            progress=0,
            frames_remaining=23,
            stability=84,
            corruption=12,
            cards_remaining=GAME_CONFIG.resources.max_cards,
            freeze_available=True,
            scan_charges=GAME_CONFIG.resources.max_scan_charges,
            remaining_guesses=GAME_CONFIG.resources.max_guesses,
        )

        self.assertEqual(score, 432)

    def test_card_effects_are_configured(self) -> None:
        self.assertEqual(card_effect("sharpen-outline", matched=True).score, 8)
        self.assertEqual(card_effect("bio-scan", matched=True).corruption, -6)
        self.assertEqual(card_effect("bio-scan", matched=False).corruption, 8)

    def test_phase_and_threat_labels_follow_thresholds(self) -> None:
        self.assertEqual(phase_label(progress=0.1, corruption=10), "原始噪声")
        self.assertEqual(phase_label(progress=0.6, corruption=80), "高压失真")
        self.assertEqual(threat_label(20), "低风险")
        self.assertEqual(threat_label(60), "高风险")


if __name__ == "__main__":
    unittest.main()
