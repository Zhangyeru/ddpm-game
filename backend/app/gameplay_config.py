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
    stability: float = 0.0
    corruption: float = 0.0
    score: int = 0


@dataclass(frozen=True)
class ActionTuning:
    step_round_stability_loss: float = 46.0
    step_round_corruption_gain: float = 92.0
    wrong_guess: RiskDelta = RiskDelta(stability=-12, corruption=14, score=-18)
    sharpen_outline: RiskDelta = RiskDelta(stability=5, corruption=-4, score=8)
    matched_card: RiskDelta = RiskDelta(stability=7, corruption=-6, score=14)
    mismatched_card: RiskDelta = RiskDelta(stability=-5, corruption=8)
    freeze: RiskDelta = RiskDelta(stability=6, corruption=5)
    pulse_scan: RiskDelta = RiskDelta(stability=-3, corruption=8)
    pulse_frame_cost_ratio: float = 1 / 24


@dataclass(frozen=True)
class ScoreTuning:
    win_base: int = 120
    early_bonus_max: int = 70
    max_time_bonus: int = 92
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
    target_round_duration_ms: int = 20_000
    min_step_interval_ms: int = 120
    session_ttl_seconds: int = 30 * 60
    corrupted_variant_threshold: int = 70
    progress_event_points: tuple[float, ...] = (0.2, 0.4, 0.6, 0.8)
    high_corruption_event_points: tuple[float, ...] = (0.25, 0.5, 0.75, 0.9)


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
    total_frames: int,
    stability: int,
    corruption: int,
    cards_remaining: int,
    freeze_available: bool,
    scan_charges: int,
    remaining_guesses: int,
) -> int:
    early_bonus = int((1 - progress) * GAME_CONFIG.scoring.early_bonus_max)
    time_bonus = calculate_time_bonus(frames_remaining=frames_remaining, total_frames=total_frames)
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


def step_risk(total_frames: int) -> RiskDelta:
    step_count = max(1, total_frames - 1)
    return RiskDelta(
        stability=-(GAME_CONFIG.actions.step_round_stability_loss / step_count),
        corruption=GAME_CONFIG.actions.step_round_corruption_gain / step_count,
    )


def pulse_frame_cost(total_frames: int) -> int:
    return max(1, round(total_frames * GAME_CONFIG.actions.pulse_frame_cost_ratio))


def calculate_time_bonus(*, frames_remaining: int, total_frames: int) -> int:
    denominator = max(1, total_frames - 1)
    ratio = max(0.0, min(1.0, frames_remaining / denominator))
    return int(round(ratio * GAME_CONFIG.scoring.max_time_bonus))


def step_interval_ms(total_frames: int) -> int:
    return max(
        GAME_CONFIG.presentation.min_step_interval_ms,
        round(GAME_CONFIG.presentation.target_round_duration_ms / max(1, total_frames)),
    )


def progress_event_frames(total_frames: int) -> frozenset[int]:
    return _milestone_frames(total_frames, GAME_CONFIG.presentation.progress_event_points)


def high_corruption_event_frames(total_frames: int) -> frozenset[int]:
    return _milestone_frames(total_frames, GAME_CONFIG.presentation.high_corruption_event_points)


def _milestone_frames(total_frames: int, points: tuple[float, ...]) -> frozenset[int]:
    last_index = max(0, total_frames - 1)
    frames = {
        max(1, min(last_index - 1, int(last_index * point)))
        for point in points
        if last_index >= 2
    }
    return frozenset(frames)
