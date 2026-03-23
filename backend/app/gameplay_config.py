from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


MissionType = Literal["speed", "stability", "precision"]


@dataclass(frozen=True)
class MissionDefinition:
    mission_type: MissionType
    title: str


@dataclass(frozen=True)
class ResourceConfig:
    max_guesses: int = 3
    max_cards: int = 2
    max_scan_charges: int = 1
    max_stability: int = 100
    max_corruption: int = 100


@dataclass(frozen=True)
class InitialSessionConfig:
    stability: int = 84
    corruption: int = 12


@dataclass(frozen=True)
class RoundStructureConfig:
    max_chapters: int = 3
    levels_per_chapter: int = 8


@dataclass(frozen=True)
class RiskDelta:
    stability: int = 0
    corruption: int = 0
    score: int = 0


@dataclass(frozen=True)
class ActionTuning:
    step: RiskDelta = RiskDelta(stability=-2, corruption=4)
    wrong_guess: RiskDelta = RiskDelta(stability=-12, corruption=14, score=-18)
    sharpen_outline: RiskDelta = RiskDelta(stability=5, corruption=-4, score=8)
    matched_card: RiskDelta = RiskDelta(stability=7, corruption=-6, score=14)
    mismatched_card: RiskDelta = RiskDelta(stability=-5, corruption=8)
    freeze: RiskDelta = RiskDelta(stability=6, corruption=5)
    pulse_scan: RiskDelta = RiskDelta(stability=-3, corruption=8)
    pulse_frame_cost: int = 1


@dataclass(frozen=True)
class ScoreTuning:
    win_base: int = 120
    early_bonus_max: int = 70
    time_bonus_per_frame: int = 4
    stability_bonus_divisor: int = 2
    corruption_bonus_base: int = 32
    corruption_bonus_divisor: int = 3
    card_use_penalty: int = 8
    freeze_use_penalty: int = 12
    pulse_use_penalty: int = 10
    speed_bonus_max: int = 80
    precision_guess_weight: int = 12
    precision_card_weight: int = 10
    precision_freeze_bonus: int = 12
    precision_scan_weight: int = 12


@dataclass(frozen=True)
class PresentationTuning:
    step_interval_ms: int = 900
    session_ttl_seconds: int = 30 * 60
    corrupted_variant_threshold: int = 70
    progress_event_frames: frozenset[int] = frozenset({4, 9, 14, 19})
    high_corruption_event_frames: frozenset[int] = frozenset({10, 16, 21})


@dataclass(frozen=True)
class GameConfig:
    initial_session: InitialSessionConfig = InitialSessionConfig()
    resources: ResourceConfig = ResourceConfig()
    rounds: RoundStructureConfig = RoundStructureConfig()
    actions: ActionTuning = ActionTuning()
    scoring: ScoreTuning = ScoreTuning()
    presentation: PresentationTuning = PresentationTuning()


GAME_CONFIG = GameConfig()

MISSION_CYCLE: tuple[MissionDefinition, ...] = (
    MissionDefinition("speed", "速判回收：越早识别，奖励越高"),
    MissionDefinition("stability", "稳态回收：保持稳定度，吃满保底收益"),
    MissionDefinition("precision", "低干预回收：少用工具，分数更优"),
)


def chapter_and_level_for_round(round_index: int) -> tuple[int, int]:
    round_offset = max(0, round_index - 1)
    chapter = min(
        GAME_CONFIG.rounds.max_chapters,
        (round_offset // GAME_CONFIG.rounds.levels_per_chapter) + 1,
    )
    level = (round_offset % GAME_CONFIG.rounds.levels_per_chapter) + 1
    return chapter, level


def mission_for_round(round_index: int) -> MissionDefinition:
    round_offset = max(0, round_index - 1)
    return MISSION_CYCLE[round_offset % len(MISSION_CYCLE)]


def mission_bonus(
    mission_type: MissionType,
    *,
    progress: float,
    stability: int,
    remaining_guesses: int,
    cards_remaining: int,
    freeze_available: bool,
    scan_charges: int,
) -> int:
    if mission_type == "speed":
        return int((1 - progress) * GAME_CONFIG.scoring.speed_bonus_max)
    if mission_type == "stability":
        return stability
    if mission_type == "precision":
        bonus = remaining_guesses * GAME_CONFIG.scoring.precision_guess_weight
        bonus += cards_remaining * GAME_CONFIG.scoring.precision_card_weight
        bonus += GAME_CONFIG.scoring.precision_freeze_bonus if freeze_available else 0
        bonus += scan_charges * GAME_CONFIG.scoring.precision_scan_weight
        return bonus
    return 0


def calculate_win_score(
    mission_type: MissionType,
    *,
    progress: float,
    frames_remaining: int,
    stability: int,
    corruption: int,
    cards_remaining: int,
    freeze_available: bool,
    scan_charges: int,
    remaining_guesses: int,
) -> int:
    early_bonus = int((1 - progress) * GAME_CONFIG.scoring.early_bonus_max)
    time_bonus = frames_remaining * GAME_CONFIG.scoring.time_bonus_per_frame
    stability_bonus = stability // GAME_CONFIG.scoring.stability_bonus_divisor
    corruption_bonus = max(
        0,
        GAME_CONFIG.scoring.corruption_bonus_base
        - (corruption // GAME_CONFIG.scoring.corruption_bonus_divisor),
    )
    tool_penalty = (
        (GAME_CONFIG.resources.max_cards - cards_remaining) * GAME_CONFIG.scoring.card_use_penalty
    )
    if not freeze_available:
        tool_penalty += GAME_CONFIG.scoring.freeze_use_penalty
    if scan_charges < GAME_CONFIG.resources.max_scan_charges:
        tool_penalty += GAME_CONFIG.scoring.pulse_use_penalty

    return (
        GAME_CONFIG.scoring.win_base
        + early_bonus
        + time_bonus
        + stability_bonus
        + corruption_bonus
        + mission_bonus(
            mission_type,
            progress=progress,
            stability=stability,
            remaining_guesses=remaining_guesses,
            cards_remaining=cards_remaining,
            freeze_available=freeze_available,
            scan_charges=scan_charges,
        )
        - tool_penalty
    )


def phase_label(*, progress: float, corruption: int) -> str:
    if corruption >= GAME_CONFIG.presentation.corrupted_variant_threshold:
        return "高压失真"
    if progress < 0.25:
        return "原始噪声"
    if progress < 0.5:
        return "轮廓锁定"
    if progress < 0.8:
        return "特征暴露"
    return "终局判断"


def threat_label(corruption: int) -> str:
    if corruption < 25:
        return "低风险"
    if corruption < 50:
        return "中风险"
    if corruption < 75:
        return "高风险"
    return "崩溃边缘"


def card_effect(card_id: str, *, matched: bool) -> RiskDelta:
    if card_id == "sharpen-outline":
        return GAME_CONFIG.actions.sharpen_outline
    if matched:
        return GAME_CONFIG.actions.matched_card
    return GAME_CONFIG.actions.mismatched_card
