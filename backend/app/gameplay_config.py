from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


MissionType = Literal["speed", "stability", "precision"]
LevelRuleId = Literal[
    "baseline",
    "family-commit",
    "freeze-choice",
    "masked-candidates",
    "rotating-echo",
    "single-card-contract",
    "dual-phase-identification",
    "noise-budget",
    "freeze-delay",
    "corruption-reorder",
    "evidence-debt",
    "final-archive",
]


@dataclass(frozen=True)
class MissionDefinition:
    mission_type: MissionType
    title: str


@dataclass(frozen=True)
class ResourceConfig:
    max_guesses: int = 3
    max_cards: int = 2
    max_stability: int = 100
    max_corruption: int = 100


@dataclass(frozen=True)
class InitialSessionConfig:
    stability: int = 84
    corruption: int = 12


@dataclass(frozen=True)
class CampaignStructureConfig:
    chapters: int = 4
    levels_per_chapter: int = 3


@dataclass(frozen=True)
class LevelDefinition:
    level_id: str
    chapter: int
    chapter_title: str
    level: int
    level_title: str
    summary: str
    rule_id: LevelRuleId
    rule_summary: str
    rule_badges: tuple[str, ...]
    mission_type: MissionType
    candidate_count: int
    max_guesses: int
    max_cards: int
    initial_stability: int
    initial_corruption: int
    risk_multiplier: float
    target_pool: tuple[str, ...]

    @property
    def mission_title(self) -> str:
        return mission_definition(self.mission_type).title


@dataclass(frozen=True)
class RiskDelta:
    stability: float = 0.0
    corruption: float = 0.0
    score: int = 0


@dataclass(frozen=True)
class ScoreBreakdownData:
    process_score_total: int = 0
    base_score: int = 0
    early_bonus: int = 0
    time_bonus: int = 0
    stability_bonus: int = 0
    low_corruption_bonus: int = 0
    mission_bonus: int = 0
    card_penalty: int = 0
    settlement_score: int = 0
    final_score: int = 0


@dataclass(frozen=True)
class ActionTuning:
    step_round_stability_loss: float = 46.0
    step_round_corruption_gain: float = 92.0
    wrong_guess: RiskDelta = RiskDelta(stability=-12, corruption=14, score=-18)
    sharpen_outline: RiskDelta = RiskDelta(stability=5, corruption=-4, score=8)
    matched_card: RiskDelta = RiskDelta(stability=7, corruption=-6, score=14)
    mismatched_card: RiskDelta = RiskDelta(stability=-5, corruption=8)


@dataclass(frozen=True)
class ScoreTuning:
    win_base: int = 120
    early_bonus_max: int = 70
    max_time_bonus: int = 92
    stability_bonus_divisor: int = 2
    corruption_bonus_base: int = 32
    corruption_bonus_divisor: int = 3
    card_use_penalty: int = 8
    speed_bonus_max: int = 80
    precision_card_weight: int = 30


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
    campaign: CampaignStructureConfig = CampaignStructureConfig()
    actions: ActionTuning = ActionTuning()
    scoring: ScoreTuning = ScoreTuning()
    presentation: PresentationTuning = PresentationTuning()


GAME_CONFIG = GameConfig()

MISSION_LIBRARY: dict[MissionType, MissionDefinition] = {
    "speed": MissionDefinition("speed", "快速识别：越早锁定目标，得分越高"),
    "stability": MissionDefinition("stability", "稳定回收：越稳越干净，结算越高"),
    "precision": MissionDefinition("precision", "少用卡牌：干预越少，额外奖励越高"),
}

LEVEL_DEFINITIONS: tuple[LevelDefinition, ...] = (
    LevelDefinition(
        level_id="chapter-1-level-1",
        chapter=1,
        chapter_title="第一章：初步校准",
        level=1,
        level_title="家养目标",
        summary="唯一的入门关，没有额外限制，适合先摸清观察、出卡与提交的节奏。",
        rule_id="baseline",
        rule_summary="基础规则：本关不启用额外限制，适合先摸清观察、出卡与提交的节奏。",
        rule_badges=("基础流程", "入门关"),
        mission_type="speed",
        candidate_count=4,
        max_guesses=3,
        max_cards=2,
        initial_stability=90,
        initial_corruption=8,
        risk_multiplier=0.82,
        target_pool=("猫", "狗", "自行车", "摩托车"),
    ),
    LevelDefinition(
        level_id="chapter-1-level-2",
        chapter=1,
        chapter_title="第一章：初步校准",
        level=2,
        level_title="先分家族",
        summary="先判断目标家族，再决定要不要动用高价值卡牌。",
        rule_id="family-commit",
        rule_summary="先选目标家族：先判断目标属于生物、机械还是建筑，错选会让对应家族卡失去优势。",
        rule_badges=("先选家族", "错选减益"),
        mission_type="stability",
        candidate_count=5,
        max_guesses=3,
        max_cards=2,
        initial_stability=88,
        initial_corruption=10,
        risk_multiplier=0.88,
        target_pool=("猫", "狗", "马", "自行车", "摩托车"),
    ),
    LevelDefinition(
        level_id="chapter-1-level-3",
        chapter=1,
        chapter_title="第一章：初步校准",
        level=3,
        level_title="谨慎干预",
        summary="首次引入区域冻结，要先看清主体位置，再决定何时出手。",
        rule_id="freeze-choice",
        rule_summary="冻结一个区域：本关可冻结 1 次画面区域，适合在看清主体位置后使用。",
        rule_badges=("一次冻结", "看清再用"),
        mission_type="precision",
        candidate_count=5,
        max_guesses=3,
        max_cards=2,
        initial_stability=86,
        initial_corruption=12,
        risk_multiplier=0.94,
        target_pool=("猫", "狗", "马", "自行车", "摩托车", "火车"),
    ),
    LevelDefinition(
        level_id="chapter-2-level-1",
        chapter=2,
        chapter_title="第二章：城市回声",
        level=1,
        level_title="混合候选",
        summary="开局有两项候选不会直接显现，只能靠推进逐步揭示。",
        rule_id="masked-candidates",
        rule_summary="隐藏候选：开局有 2 个候选不会直接显示，随着推进逐步揭示。",
        rule_badges=("隐藏候选", "逐步揭示"),
        mission_type="speed",
        candidate_count=6,
        max_guesses=3,
        max_cards=2,
        initial_stability=82,
        initial_corruption=16,
        risk_multiplier=1.0,
        target_pool=("猫", "狗", "马", "鹰", "自行车", "摩托车"),
    ),
    LevelDefinition(
        level_id="chapter-2-level-2",
        chapter=2,
        chapter_title="第二章：城市回声",
        level=2,
        level_title="建筑混入",
        summary="阶段点会替换一项诱饵候选，不能只靠记忆排除答案。",
        rule_id="rotating-echo",
        rule_summary="诱饵会变化：阶段点会替换 1 个干扰候选，不能只靠记忆排除答案。",
        rule_badges=("诱饵变动", "别凭记忆"),
        mission_type="stability",
        candidate_count=6,
        max_guesses=3,
        max_cards=2,
        initial_stability=80,
        initial_corruption=18,
        risk_multiplier=1.05,
        target_pool=("马", "鹰", "自行车", "摩托车", "火车", "城堡", "灯塔"),
    ),
    LevelDefinition(
        level_id="chapter-2-level-3",
        chapter=2,
        chapter_title="第二章：城市回声",
        level=3,
        level_title="单卡定局",
        summary="首张卡会锁定本局路线，出手前要先想清楚。",
        rule_id="single-card-contract",
        rule_summary="首张卡锁定：本局打出的第一张卡会锁定其余卡牌，路线要提前决定。",
        rule_badges=("首卡锁定", "只能走一条"),
        mission_type="precision",
        candidate_count=6,
        max_guesses=3,
        max_cards=1,
        initial_stability=80,
        initial_corruption=18,
        risk_multiplier=1.08,
        target_pool=("猫", "鹰", "自行车", "摩托车", "城堡", "灯塔"),
    ),
    LevelDefinition(
        level_id="chapter-3-level-1",
        chapter=3,
        chapter_title="第三章：失稳边缘",
        level=1,
        level_title="先分类再判断",
        summary="本关必须先判家族，再锁定具体目标，不能跳过这一步。",
        rule_id="dual-phase-identification",
        rule_summary="先分类后猜测：必须先完成家族判断，才能提交具体目标。",
        rule_badges=("先分类", "后猜目标"),
        mission_type="speed",
        candidate_count=6,
        max_guesses=2,
        max_cards=2,
        initial_stability=78,
        initial_corruption=20,
        risk_multiplier=1.12,
        target_pool=("狗", "马", "鹰", "火车", "飞机", "灯塔"),
    ),
    LevelDefinition(
        level_id="chapter-3-level-2",
        chapter=3,
        chapter_title="第三章：失稳边缘",
        level=2,
        level_title="连推风险",
        summary="连续推进会额外抬高污染，拖得越久越难收场。",
        rule_id="noise-budget",
        rule_summary="连续推进更危险：连续推进会额外提升污染，不能只靠多看几步。",
        rule_badges=("连推危险", "节奏重要"),
        mission_type="stability",
        candidate_count=7,
        max_guesses=2,
        max_cards=2,
        initial_stability=76,
        initial_corruption=24,
        risk_multiplier=1.16,
        target_pool=("猫", "狗", "马", "鹰", "摩托车", "火车", "城堡"),
    ),
    LevelDefinition(
        level_id="chapter-3-level-3",
        chapter=3,
        chapter_title="第三章：失稳边缘",
        level=3,
        level_title="冻结有代价",
        summary="冻结不再是纯收益，时机不对，反而会让下一步更难受。",
        rule_id="freeze-delay",
        rule_summary="冻结后的额外代价：冻结后下一次推进会额外消耗解码窗口。",
        rule_badges=("冻结有代价", "慎选时机"),
        mission_type="precision",
        candidate_count=7,
        max_guesses=2,
        max_cards=1,
        initial_stability=74,
        initial_corruption=26,
        risk_multiplier=1.18,
        target_pool=("猫", "马", "鹰", "自行车", "火车", "飞机", "城堡"),
    ),
    LevelDefinition(
        level_id="chapter-4-level-1",
        chapter=4,
        chapter_title="第四章：最终归档",
        level=1,
        level_title="污染后重排",
        summary="污染过线后，候选顺序和工具权限都会变化，必须提前下判断。",
        rule_id="corruption-reorder",
        rule_summary="污染过线会变局：污染达到阈值后，候选会重排，还会禁用一张高价值卡。",
        rule_badges=("过线变局", "候选重排"),
        mission_type="speed",
        candidate_count=7,
        max_guesses=2,
        max_cards=1,
        initial_stability=70,
        initial_corruption=30,
        risk_multiplier=1.22,
        target_pool=("狗", "鹰", "摩托车", "自行车", "火车", "飞机", "灯塔"),
    ),
    LevelDefinition(
        level_id="chapter-4-level-2",
        chapter=4,
        chapter_title="第四章：最终归档",
        level=2,
        level_title="出卡会欠分",
        summary="每次出卡都会留下扣分负担，只有低污染过关才能豁免。",
        rule_id="evidence-debt",
        rule_summary="高污染会额外扣分：出卡会累积债务，高污染获胜时会追加扣分。",
        rule_badges=("高污染扣分", "卡牌留痕"),
        mission_type="stability",
        candidate_count=7,
        max_guesses=2,
        max_cards=1,
        initial_stability=68,
        initial_corruption=34,
        risk_multiplier=1.26,
        target_pool=("猫", "马", "摩托车", "火车", "飞机", "城堡", "灯塔"),
    ),
    LevelDefinition(
        level_id="chapter-4-level-3",
        chapter=4,
        chapter_title="第四章：最终归档",
        level=3,
        level_title="最终综合关",
        summary="要先分类、再冻结，还要在隐藏候选里完成最后判定。",
        rule_id="final-archive",
        rule_summary="最终规则：需要先分类，再冻结，还要在隐藏候选中完成判断。",
        rule_badges=("分类+冻结", "最终考验", "隐藏候选"),
        mission_type="precision",
        candidate_count=8,
        max_guesses=2,
        max_cards=1,
        initial_stability=66,
        initial_corruption=36,
        risk_multiplier=1.32,
        target_pool=("猫", "狗", "马", "鹰", "摩托车", "火车", "城堡", "灯塔", "飞机"),
    ),
)

_LEVELS_BY_ID = {level.level_id: level for level in LEVEL_DEFINITIONS}


def mission_definition(mission_type: MissionType) -> MissionDefinition:
    return MISSION_LIBRARY[mission_type]


def first_level() -> LevelDefinition:
    return LEVEL_DEFINITIONS[0]


def all_levels() -> tuple[LevelDefinition, ...]:
    return LEVEL_DEFINITIONS


def level_by_id(level_id: str) -> LevelDefinition:
    return _LEVELS_BY_ID[level_id]


def next_level(level_id: str) -> LevelDefinition | None:
    for index, definition in enumerate(LEVEL_DEFINITIONS):
        if definition.level_id != level_id:
            continue
        if index + 1 >= len(LEVEL_DEFINITIONS):
            return None
        return LEVEL_DEFINITIONS[index + 1]
    raise KeyError(level_id)


def mission_bonus(
    mission_type: MissionType,
    *,
    progress: float,
    stability: int,
    cards_remaining: int,
) -> int:
    if mission_type == "speed":
        return int((1 - progress) * GAME_CONFIG.scoring.speed_bonus_max)
    if mission_type == "stability":
        return stability
    if mission_type == "precision":
        return cards_remaining * GAME_CONFIG.scoring.precision_card_weight
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
    max_cards_total: int | None = None,
) -> int:
    return calculate_score_breakdown(
        mission_type,
        progress=progress,
        frames_remaining=frames_remaining,
        total_frames=total_frames,
        stability=stability,
        corruption=corruption,
        cards_remaining=cards_remaining,
        max_cards_total=max_cards_total,
    ).settlement_score


def calculate_score_breakdown(
    mission_type: MissionType,
    *,
    progress: float,
    frames_remaining: int,
    total_frames: int,
    stability: int,
    corruption: int,
    cards_remaining: int,
    process_score_total: int = 0,
    max_cards_total: int | None = None,
) -> ScoreBreakdownData:
    early_bonus = int((1 - progress) * GAME_CONFIG.scoring.early_bonus_max)
    time_bonus = calculate_time_bonus(frames_remaining=frames_remaining, total_frames=total_frames)
    stability_bonus = stability // GAME_CONFIG.scoring.stability_bonus_divisor
    low_corruption_bonus = max(
        0,
        GAME_CONFIG.scoring.corruption_bonus_base
        - (corruption // GAME_CONFIG.scoring.corruption_bonus_divisor),
    )
    total_cards = GAME_CONFIG.resources.max_cards if max_cards_total is None else max_cards_total
    card_penalty = (max(0, total_cards - cards_remaining)) * GAME_CONFIG.scoring.card_use_penalty
    mission_reward = mission_bonus(
        mission_type,
        progress=progress,
        stability=stability,
        cards_remaining=cards_remaining,
    )
    settlement_score = (
        GAME_CONFIG.scoring.win_base
        + early_bonus
        + time_bonus
        + stability_bonus
        + low_corruption_bonus
        + mission_reward
        - card_penalty
    )
    return ScoreBreakdownData(
        process_score_total=process_score_total,
        base_score=GAME_CONFIG.scoring.win_base,
        early_bonus=early_bonus,
        time_bonus=time_bonus,
        stability_bonus=stability_bonus,
        low_corruption_bonus=low_corruption_bonus,
        mission_bonus=mission_reward,
        card_penalty=card_penalty,
        settlement_score=settlement_score,
        final_score=process_score_total + settlement_score,
    )


def calculate_loss_breakdown(*, process_score_total: int) -> ScoreBreakdownData:
    return ScoreBreakdownData(
        process_score_total=process_score_total,
        final_score=process_score_total,
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


def step_risk(total_frames: int, *, risk_multiplier: float = 1.0) -> RiskDelta:
    step_count = max(1, total_frames - 1)
    return RiskDelta(
        stability=-(GAME_CONFIG.actions.step_round_stability_loss * risk_multiplier / step_count),
        corruption=GAME_CONFIG.actions.step_round_corruption_gain * risk_multiplier / step_count,
    )


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


def describe_level_transition(current: LevelDefinition, upcoming: LevelDefinition) -> str:
    changes: list[str] = []
    if upcoming.candidate_count != current.candidate_count:
        changes.append(f"候选改为 {upcoming.candidate_count} 项")
    if upcoming.max_guesses != current.max_guesses:
        changes.append(f"猜测次数改为 {upcoming.max_guesses} 次")
    if upcoming.max_cards != current.max_cards:
        changes.append(f"卡牌改为 {upcoming.max_cards} 张")
    if upcoming.initial_stability < current.initial_stability:
        changes.append(f"初始稳定降到 {upcoming.initial_stability}")
    if upcoming.initial_corruption > current.initial_corruption:
        changes.append(f"初始污染升到 {upcoming.initial_corruption}")
    if upcoming.risk_multiplier > current.risk_multiplier + 0.01:
        changes.append("每步风险更高")
    if not changes:
        return upcoming.summary
    return f"下一关：{'，'.join(changes[:4])}。"


def _milestone_frames(total_frames: int, points: tuple[float, ...]) -> frozenset[int]:
    last_index = max(0, total_frames - 1)
    frames = {
        max(1, min(last_index - 1, int(last_index * point)))
        for point in points
        if last_index >= 2
    }
    return frozenset(frames)
