from __future__ import annotations

import unittest

from backend.app.gameplay_config import (
    GAME_CONFIG,
    all_levels,
    calculate_score_breakdown,
    calculate_win_score,
    card_effect,
    first_level,
    high_corruption_event_frames,
    level_by_id,
    next_level,
    phase_label,
    progress_event_frames,
    step_interval_ms,
    step_risk,
    threat_label,
)


class GameplayConfigTest(unittest.TestCase):
    def test_campaign_defines_twelve_levels(self) -> None:
        levels = all_levels()

        self.assertEqual(
            len(levels),
            GAME_CONFIG.campaign.chapters * GAME_CONFIG.campaign.levels_per_chapter,
        )
        self.assertEqual(first_level().level_id, "chapter-1-level-1")
        self.assertEqual(levels[-1].level_id, "chapter-4-level-3")
        self.assertIsNone(next_level("chapter-4-level-3"))
        self.assertEqual(next_level("chapter-1-level-1").level_id, "chapter-1-level-2")  # type: ignore[union-attr]

    def test_level_lookup_returns_expected_tuning(self) -> None:
        level = level_by_id("chapter-3-level-2")

        self.assertEqual(level.chapter_title, "第三章：高压回路")
        self.assertEqual(level.level_title, "稳态压测")
        self.assertEqual(level.mission_type, "stability")
        self.assertEqual(level.candidate_count, 7)
        self.assertEqual(level.max_guesses, 2)
        self.assertEqual(level.max_cards, 2)

    def test_calculate_win_score_uses_default_tuning(self) -> None:
        score = calculate_win_score(
            "speed",
            progress=0,
            frames_remaining=23,
            total_frames=24,
            stability=84,
            corruption=12,
            cards_remaining=GAME_CONFIG.resources.max_cards,
        )

        self.assertEqual(score, 432)

    def test_score_breakdown_sums_to_final_score(self) -> None:
        breakdown = calculate_score_breakdown(
            "precision",
            progress=0.25,
            frames_remaining=60,
            total_frames=100,
            stability=70,
            corruption=30,
            cards_remaining=0,
            max_cards_total=1,
            process_score_total=22,
        )

        self.assertEqual(
            breakdown.final_score,
            breakdown.process_score_total + breakdown.settlement_score,
        )
        self.assertEqual(
            breakdown.settlement_score,
            breakdown.base_score
            + breakdown.early_bonus
            + breakdown.time_bonus
            + breakdown.stability_bonus
            + breakdown.low_corruption_bonus
            + breakdown.mission_bonus
            - breakdown.card_penalty,
        )
        self.assertEqual(breakdown.card_penalty, GAME_CONFIG.scoring.card_use_penalty)

    def test_dynamic_step_tuning_scales_with_total_frames_and_multiplier(self) -> None:
        self.assertEqual(step_interval_ms(100), 200)
        self.assertEqual(progress_event_frames(100), frozenset({19, 39, 59, 79}))
        self.assertEqual(high_corruption_event_frames(100), frozenset({24, 49, 74, 89}))

        risk = step_risk(100, risk_multiplier=1.2)
        self.assertAlmostEqual(risk.stability, -(46 * 1.2) / 99)
        self.assertAlmostEqual(risk.corruption, (92 * 1.2) / 99)

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
