from __future__ import annotations

import hashlib
import hmac
import random
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Callable

from .auth import PlayerCampaignProgress, SQLiteAuthStore, is_user_actor, user_id_from_actor
from .frame_renderer import DEFAULT_TOTAL_FRAMES
from .game_data import (
    CARD_DEFINITIONS,
    FREEZE_REGION_DEFINITIONS,
    TARGETS,
    TargetDefinition,
)
from .gameplay_config import (
    GAME_CONFIG,
    LEVEL_DEFINITIONS,
    LevelDefinition,
    LevelRuleId,
    MissionType,
    ScoreBreakdownData,
    all_levels,
    calculate_loss_breakdown,
    calculate_score_breakdown,
    card_effect,
    describe_level_transition,
    first_level,
    high_corruption_event_frames,
    level_by_id,
    mission_definition,
    phase_label,
    progress_event_frames,
    step_interval_ms,
    step_risk,
    threat_label,
    next_level as resolve_next_level,
)
from .schemas import (
    CardOption,
    LevelProgressItem,
    ProgressSnapshot,
    ScoreBreakdown,
    ScoreEvent,
    SessionSnapshot,
    TargetFamily,
)
from .trajectory_store import FrameAsset, TrajectoryStore


SESSION_TTL_SECONDS = GAME_CONFIG.presentation.session_ttl_seconds
MAX_STABILITY = GAME_CONFIG.resources.max_stability
MAX_CORRUPTION = GAME_CONFIG.resources.max_corruption
MASKED_CANDIDATE_LABEL = "未知信号"
FAMILY_LABELS: dict[str, str] = {
    "living": "生物",
    "machine": "机械",
    "structure": "建筑",
}
CARD_DISABLE_PRIORITY = ("mechanical-lens", "bio-scan", "sharpen-outline")


@dataclass
class Session:
    session_id: str
    player_id: str
    frame_secret: str
    sample_id: str
    level_id: str
    chapter: int
    level: int
    chapter_title: str
    level_title: str
    level_summary: str
    level_rule_id: LevelRuleId
    rule_summary: str
    rule_badges: tuple[str, ...]
    mission_type: MissionType
    mission_title: str
    target: TargetDefinition
    candidate_labels: list[str]
    max_guesses: int
    max_cards: int
    risk_multiplier: float
    hidden_candidate_indices: set[int] = field(default_factory=set)
    rotating_echo_index: int | None = None
    rotating_echo_pool: list[str] = field(default_factory=list)
    objective_phase: str = "standard"
    committed_family: str | None = None
    freeze_remaining: int = 0
    frozen_region: str | None = None
    disabled_card_ids: list[str] = field(default_factory=list)
    step_streak: int = 0
    threshold_triggered: bool = False
    evidence_debt: int = 0
    freeze_step_tax_pending: bool = False
    score: int = 0
    combo: int = 0
    status: str = "playing"
    frames_remaining: int = 0
    stability: float = 0.0
    corruption: float = 0.0
    frame_index: int = 0
    total_frames: int = DEFAULT_TOTAL_FRAMES
    remaining_guesses: int = 0
    cards_remaining: int = 0
    hint: str = ""
    events: list[str] = field(default_factory=list)
    used_cards: list[str] = field(default_factory=list)
    score_events: list[ScoreEvent] = field(default_factory=list)
    score_breakdown: ScoreBreakdown | None = None
    loss_reason: str | None = None
    ended_at: str | None = None
    revealed_target: str | None = None
    awaiting_advancement: bool = False
    next_level_id: str | None = None
    next_level_title: str | None = None
    next_level_summary: str | None = None
    campaign_complete: bool = False
    level_best_score: int | None = None
    level_best_improved: bool = False
    last_touched_at: float = field(default_factory=time.monotonic)


class GameService:
    def __init__(
        self,
        trajectory_store: TrajectoryStore | None = None,
        *,
        auth_store: SQLiteAuthStore | None = None,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self.trajectory_store = trajectory_store or TrajectoryStore()
        self.auth_store = auth_store
        self.clock = clock or time.monotonic
        self.sessions: dict[str, Session] = {}
        self.player_progress: dict[str, PlayerCampaignProgress] = {}
        self.targets_by_label = {
            target.label: target
            for target in TARGETS
            if self.trajectory_store.has_target(target.label)
        }
        self.levels = all_levels()
        self.level_indices = {level.level_id: index for index, level in enumerate(self.levels)}
        self.card_options = tuple(
            CardOption(
                id=card_id,
                title=definition.title,
                summary=definition.summary,
            )
            for card_id, definition in CARD_DEFINITIONS.items()
        )
        self._lock = RLock()
        if len(self.targets_by_label) < 6:
            raise ValueError("轨迹清单中的可用目标不足 6 个，无法生成候选列表。")
        self._validate_level_definitions()

    def get_progression(self, player_id: str | None) -> ProgressSnapshot:
        player_key = self._normalize_player_id(player_id)
        with self._lock:
            progress = self._campaign_progress(player_key)
            return self._progression_snapshot(progress)

    def start_session(self, player_id: str | None) -> SessionSnapshot:
        return self.start_current_level(player_id)

    def start_current_level(self, player_id: str | None) -> SessionSnapshot:
        player_key = self._normalize_player_id(player_id)
        with self._lock:
            self._prune_expired_sessions()
            progress = self._campaign_progress(player_key)
            level_definition = level_by_id(progress.current_level_id)
            session = self._build_session(player_key, progress, level_definition)
            self.sessions[session.session_id] = session
            return self._snapshot(session)

    def advance(self, player_id: str | None, session_id: str) -> SessionSnapshot:
        with self._lock:
            session = self._get_session(player_id, session_id)
            if session.status != "won":
                raise ValueError("只有通关后的回收记录才能推进下一关。")
            progress = self._campaign_progress(session.player_id)
            if session.next_level_id is not None and progress.current_level_id != session.level_id:
                current_definition = level_by_id(progress.current_level_id)
                current_session = self._build_session(
                    session.player_id,
                    progress,
                    current_definition,
                )
                self.sessions[current_session.session_id] = current_session
                return self._snapshot(current_session)
            if session.awaiting_advancement is False or session.next_level_id is None:
                raise ValueError("当前没有可推进的下一关。")

            progress.current_level_id = session.next_level_id
            self._save_campaign_progress(session.player_id, progress)
            session.awaiting_advancement = False
            next_definition = level_by_id(session.next_level_id)
            next_session = self._build_session(session.player_id, progress, next_definition)
            self.sessions[next_session.session_id] = next_session
            return self._snapshot(next_session)

    def step(self, player_id: str | None, session_id: str) -> SessionSnapshot:
        with self._lock:
            session = self._get_session(player_id, session_id)
            if session.status != "playing":
                return self._snapshot(session)

            session.step_streak += 1
            session.frame_index = min(session.total_frames - 1, session.frame_index + 1)
            session.frames_remaining = max(0, session.frames_remaining - 1)
            step_delta = step_risk(session.total_frames, risk_multiplier=session.risk_multiplier)
            extra_stability_delta, extra_corruption_delta = self._step_rule_adjustments(session)
            self._shift_risk(
                session,
                stability_delta=step_delta.stability + extra_stability_delta,
                corruption_delta=step_delta.corruption + extra_corruption_delta,
            )

            if session.frame_index in progress_event_frames(session.total_frames):
                self._append_event(session, self._progress_message(session))
                self._apply_progression_rule_updates(session)

            if (
                session.corruption >= GAME_CONFIG.presentation.corrupted_variant_threshold
                and session.frame_index in high_corruption_event_frames(session.total_frames)
            ):
                self._append_event(session, "污染度过高，画面开始出现伪轮廓和裂缝。")

            self._apply_threshold_rule_updates(session)
            self._resolve_if_failed(session)
            return self._snapshot(session)

    def guess(self, player_id: str | None, session_id: str, label: str) -> SessionSnapshot:
        with self._lock:
            session = self._get_session(player_id, session_id)
            if session.status != "playing":
                return self._snapshot(session)

            guess = label.strip()
            if not guess:
                raise ValueError("猜测不能为空。")
            if session.level_rule_id in {"dual-phase-identification", "final-archive"} and session.objective_phase == "classify":
                raise ValueError("当前关卡需要先完成家族判定。")
            if guess not in self._guessable_labels(session):
                raise ValueError("猜测必须来自当前候选列表。")

            if guess == session.target.label:
                progress_ratio = session.frame_index / max(session.total_frames - 1, 1)
                breakdown = calculate_score_breakdown(
                    session.mission_type,
                    progress=progress_ratio,
                    frames_remaining=session.frames_remaining,
                    total_frames=session.total_frames,
                    stability=round(session.stability),
                    corruption=round(session.corruption),
                    cards_remaining=session.cards_remaining,
                    process_score_total=session.score,
                    max_cards_total=session.max_cards,
                )
                breakdown = self._apply_settlement_rule_adjustments(session, breakdown)
                session.score = breakdown.final_score
                session.combo = self._record_win(session.player_id)
                session.status = "won"
                session.revealed_target = session.target.label
                session.score_breakdown = self._score_breakdown_model(breakdown)
                session.ended_at = self._ended_at_iso()
                self._append_score_event(
                    session,
                    kind="settlement",
                    title="最终结算",
                    delta=breakdown.settlement_score,
                    detail=self._settlement_detail(breakdown),
                )
                self._append_rule_settlement_events(session)
                self._complete_level(session)
                self._append_event(
                    session,
                    f"识别正确，遗物确认为：{session.target.label}。",
                )
                return self._snapshot(session)

            session.step_streak = 0
            session.remaining_guesses = max(0, session.remaining_guesses - 1)
            session.score += GAME_CONFIG.actions.wrong_guess.score
            self._shift_risk(
                session,
                stability_delta=GAME_CONFIG.actions.wrong_guess.stability,
                corruption_delta=GAME_CONFIG.actions.wrong_guess.corruption,
            )
            self._append_score_event(
                session,
                kind="guess_penalty",
                title="错误猜测",
                delta=GAME_CONFIG.actions.wrong_guess.score,
                detail=(
                    f"提交 {guess} 失败。稳定度 {GAME_CONFIG.actions.wrong_guess.stability}，"
                    f"污染 +{GAME_CONFIG.actions.wrong_guess.corruption}。"
                ),
            )
            self._append_event(session, f"猜测错误：{guess}。信号再次变得不稳定。")

            self._resolve_if_failed(session)
            return self._snapshot(session)

    def use_card(self, player_id: str | None, session_id: str, card_id: str) -> SessionSnapshot:
        with self._lock:
            session = self._get_session(player_id, session_id)
            if session.status != "playing":
                return self._snapshot(session)
            if card_id not in CARD_DEFINITIONS:
                raise ValueError("未知卡牌。")
            if self._card_blocked(session, card_id):
                return self._snapshot(session)
            if session.level_rule_id == "family-commit" and session.committed_family is None and card_id != "sharpen-outline":
                raise ValueError("本关需要先提交目标家族，才能启用家族卡。")

            session.used_cards.append(card_id)
            session.cards_remaining -= 1
            definition = CARD_DEFINITIONS[card_id]
            matched = self._card_matches_target(session, card_id)
            effect = card_effect(card_id, matched=matched)
            session.step_streak = 0

            self._shift_risk(
                session,
                stability_delta=effect.stability,
                corruption_delta=effect.corruption,
            )
            session.score += effect.score

            if card_id == "sharpen-outline":
                effect_text = "轮廓稳定度上升。"
            elif matched:
                effect_text = "共振匹配，图像结构明显增强。"
            else:
                effect_text = "共振失配，画面被错误特征污染。"

            self._append_event(
                session,
                f"已使用卡牌：{definition.title}。{definition.summary}{effect_text}",
            )
            self._append_score_event(
                session,
                kind="card",
                title=definition.title,
                delta=effect.score,
                detail=self._card_score_detail(
                    card_id=card_id,
                    matched=matched,
                    stability_delta=effect.stability,
                    corruption_delta=effect.corruption,
                ),
            )
            self._apply_post_card_rule_updates(session, card_id=card_id, matched=matched)

            self._resolve_if_failed(session)
            return self._snapshot(session)

    def commit_family(
        self,
        player_id: str | None,
        session_id: str,
        family: TargetFamily,
    ) -> SessionSnapshot:
        with self._lock:
            session = self._get_session(player_id, session_id)
            if session.status != "playing":
                return self._snapshot(session)
            if not self._requires_family_commit(session):
                raise ValueError("当前关卡不需要提交目标家族。")
            if session.committed_family is not None:
                raise ValueError("本局已经提交过目标家族。")

            session.step_streak = 0
            session.committed_family = family
            if session.level_rule_id in {"dual-phase-identification", "final-archive"}:
                session.objective_phase = "identify"

            if family == session.target.family:
                self._append_event(session, f"家族判定已锁定为：{FAMILY_LABELS[family]}。共振方向正确。")
                self._append_score_event(
                    session,
                    kind="rule",
                    title="家族判定",
                    delta=6,
                    detail="家族判定正确，后续判断路线更稳定。",
                )
                session.score += 6
                session.stability = min(MAX_STABILITY, session.stability + 4)
            else:
                self._append_event(session, f"家族判定已锁定为：{FAMILY_LABELS[family]}。共振方向错误。")
                if session.level_rule_id == "family-commit":
                    session.disabled_card_ids.extend(
                        card_id
                        for card_id in ("mechanical-lens", "bio-scan")
                        if card_id not in session.disabled_card_ids
                    )
                self._append_score_event(
                    session,
                    kind="rule",
                    title="错误承诺",
                    delta=-8,
                    detail="家族判定错误，后续高价值家族卡会失去优势。",
                )
                session.score -= 8
                self._shift_risk(session, stability_delta=-4, corruption_delta=6)

            self._resolve_if_failed(session)
            return self._snapshot(session)

    def freeze(
        self,
        player_id: str | None,
        session_id: str,
        region: str,
    ) -> SessionSnapshot:
        with self._lock:
            session = self._get_session(player_id, session_id)
            if session.status != "playing":
                return self._snapshot(session)
            if region not in FREEZE_REGION_DEFINITIONS:
                raise ValueError("未知冻结区域。")
            if session.freeze_remaining <= 0:
                raise ValueError("当前没有可用冻结次数。")
            if session.frozen_region is not None:
                raise ValueError("本局已经完成区域冻结。")

            session.step_streak = 0
            session.freeze_remaining -= 1
            session.frozen_region = region
            self._shift_risk(session, stability_delta=4, corruption_delta=-3)
            if session.level_rule_id in {"freeze-delay", "final-archive"}:
                session.freeze_step_tax_pending = True
            self._append_event(
                session,
                f"已冻结 {FREEZE_REGION_DEFINITIONS[region].title}，后续显影将优先保留该区域结构。",
            )
            self._append_score_event(
                session,
                kind="rule",
                title="区域冻结",
                delta=4,
                detail=f"冻结 {FREEZE_REGION_DEFINITIONS[region].title}，稳定 +4，污染 -3。",
            )
            session.score += 4
            self._resolve_if_failed(session)
            return self._snapshot(session)

    def render_frame(
        self,
        session_id: str,
        frame_index: int,
        variant_key: str,
        token: str,
    ) -> FrameAsset:
        with self._lock:
            self._prune_expired_sessions()
            session = self.sessions.get(session_id)
            if session is None:
                raise KeyError("未找到该局游戏。")
            if variant_key not in self.trajectory_store.variant_keys:
                raise ValueError("未知轨迹变体。")
            if not 0 <= frame_index < session.total_frames:
                raise ValueError("帧索引超出范围。")
            expected_token = self._frame_token(session, frame_index, variant_key)
            if not hmac.compare_digest(expected_token, token):
                raise PermissionError("帧令牌无效。")

            session.last_touched_at = self.clock()
            return self.trajectory_store.get_frame(
                target_label=session.target.label,
                sample_id=session.sample_id,
                frame_index=frame_index,
                variant_key=variant_key,
            )

    def _campaign_progress(self, player_id: str | None) -> PlayerCampaignProgress:
        player_key = self._normalize_player_id(player_id)
        if is_user_actor(player_key) and self.auth_store is not None:
            return self.auth_store.get_or_create_progress(user_id_from_actor(player_key))
        return self.player_progress.setdefault(player_key, PlayerCampaignProgress())

    def _save_campaign_progress(
        self,
        player_id: str | None,
        progress: PlayerCampaignProgress,
    ) -> None:
        player_key = self._normalize_player_id(player_id)
        if is_user_actor(player_key) and self.auth_store is not None:
            self.auth_store.save_progress(user_id_from_actor(player_key), progress)
            return
        self.player_progress[player_key] = progress

    def _build_session(
        self,
        player_key: str,
        progress: PlayerCampaignProgress,
        level_definition: LevelDefinition,
    ) -> Session:
        rng = random.Random()
        level_targets = [self.targets_by_label[label] for label in level_definition.target_pool]
        target = rng.choice(level_targets)
        distractor_labels = [candidate.label for candidate in level_targets if candidate != target]
        candidate_labels = rng.sample(distractor_labels, k=level_definition.candidate_count - 1)
        candidate_labels.append(target.label)
        rng.shuffle(candidate_labels)
        total_frames = self.trajectory_store.total_frames
        sample_id = rng.choice(self.trajectory_store.sample_ids_for_target(target.label))

        session_id = uuid.uuid4().hex
        session = Session(
            session_id=session_id,
            player_id=player_key,
            frame_secret=uuid.uuid4().hex,
            sample_id=sample_id,
            level_id=level_definition.level_id,
            chapter=level_definition.chapter,
            level=level_definition.level,
            chapter_title=level_definition.chapter_title,
            level_title=level_definition.level_title,
            level_summary=level_definition.summary,
            level_rule_id=level_definition.rule_id,
            rule_summary=level_definition.rule_summary,
            rule_badges=level_definition.rule_badges,
            mission_type=level_definition.mission_type,
            mission_title=level_definition.mission_title,
            target=target,
            candidate_labels=candidate_labels,
            max_guesses=level_definition.max_guesses,
            max_cards=level_definition.max_cards,
            risk_multiplier=level_definition.risk_multiplier,
            combo=progress.streak,
            frames_remaining=max(total_frames - 1, 0),
            stability=level_definition.initial_stability,
            corruption=level_definition.initial_corruption,
            total_frames=total_frames,
            remaining_guesses=level_definition.max_guesses,
            cards_remaining=level_definition.max_cards,
            hint=target.hint,
            level_best_score=progress.best_scores_by_level.get(level_definition.level_id),
            events=[
                f"{level_definition.chapter_title} · 第 {level_definition.level} 关：{level_definition.level_title}。",
                level_definition.summary,
                f"规则：{level_definition.rule_summary}",
                f"分类提示：{target.hint}。",
                f"当前任务：{level_definition.mission_title}。",
            ],
            last_touched_at=self.clock(),
        )
        self._initialize_rule_state(session)
        return session

    def _complete_level(self, session: Session) -> None:
        progress = self._campaign_progress(session.player_id)
        progress.completed_level_ids.add(session.level_id)
        self._update_level_best_score(progress, session)
        current_level = level_by_id(session.level_id)
        upcoming = resolve_next_level(session.level_id)
        if upcoming is None:
            progress.highest_unlocked_level_id = current_level.level_id
            progress.current_level_id = first_level().level_id
            progress.campaign_complete = True
            session.awaiting_advancement = False
            session.campaign_complete = True
            session.next_level_id = None
            session.next_level_title = None
            session.next_level_summary = "已完成全部 12 关。你可以从第一关重新挑战整套档案。"
            self._append_event(session, "终端审判完成，整套档案已归档。")
            self._save_campaign_progress(session.player_id, progress)
            return

        session.awaiting_advancement = True
        session.next_level_id = upcoming.level_id
        session.next_level_title = upcoming.level_title
        session.next_level_summary = describe_level_transition(current_level, upcoming)
        if self.level_indices[upcoming.level_id] > self.level_indices[progress.highest_unlocked_level_id]:
            progress.highest_unlocked_level_id = upcoming.level_id
        self._append_event(
            session,
            f"已解锁下一关：第 {upcoming.chapter}-{upcoming.level} 关 {upcoming.level_title}。",
        )
        self._save_campaign_progress(session.player_id, progress)

    def _get_session(self, player_id: str | None, session_id: str) -> Session:
        self._prune_expired_sessions()
        player_key = self._normalize_player_id(player_id)
        session = self.sessions.get(session_id)
        if session is None or session.player_id != player_key:
            raise KeyError("未找到该局游戏。")

        session.last_touched_at = self.clock()
        return session

    def _record_win(self, player_id: str | None) -> int:
        progress = self._campaign_progress(player_id)
        progress.streak += 1
        self._save_campaign_progress(player_id, progress)
        return progress.streak

    def _record_loss(self, player_id: str | None) -> None:
        progress = self._campaign_progress(player_id)
        progress.streak = 0
        self._save_campaign_progress(player_id, progress)

    def _append_event(self, session: Session, message: str) -> None:
        session.events.append(message)
        if len(session.events) > 8:
            session.events = session.events[-8:]

    def _append_score_event(
        self,
        session: Session,
        *,
        kind: str,
        title: str,
        delta: int,
        detail: str,
    ) -> None:
        session.score_events.append(
            ScoreEvent(
                kind=kind,
                title=title,
                delta=delta,
                running_score=session.score,
                detail=detail,
            )
        )

    def _shift_risk(
        self,
        session: Session,
        *,
        stability_delta: float = 0.0,
        corruption_delta: float = 0.0,
    ) -> None:
        session.stability = max(0, min(MAX_STABILITY, session.stability + stability_delta))
        session.corruption = max(0, min(MAX_CORRUPTION, session.corruption + corruption_delta))

    def _resolve_if_failed(self, session: Session) -> None:
        if session.status != "playing":
            return

        reason: str | None = None
        if session.remaining_guesses <= 0:
            reason = "猜测次数耗尽。"
        elif session.stability <= 0:
            reason = "稳定度归零，信号彻底塌陷。"
        elif session.corruption >= MAX_CORRUPTION:
            reason = "污染度爆表，伪轮廓完全吞没真目标。"
        elif session.frames_remaining <= 0:
            reason = "解码窗口已关闭。"

        if reason is None:
            return

        self._record_loss(session.player_id)
        session.combo = 0
        session.status = "lost"
        session.loss_reason = reason
        session.score_breakdown = self._score_breakdown_model(
            calculate_loss_breakdown(process_score_total=session.score)
        )
        progress = self._campaign_progress(session.player_id)
        self._update_level_best_score(progress, session)
        self._save_campaign_progress(session.player_id, progress)
        session.ended_at = self._ended_at_iso()
        session.revealed_target = session.target.label
        session.awaiting_advancement = False
        session.campaign_complete = False
        self._append_score_event(
            session,
            kind="loss",
            title="本局失败",
            delta=0,
            detail=f"{reason} 隐藏目标是：{session.target.label}。",
        )
        self._append_event(session, f"{reason} 隐藏目标是：{session.target.label}。")

    def _progress_message(self, session: Session) -> str:
        progress = session.frame_index / max(session.total_frames - 1, 1)
        if progress < 0.25:
            return "噪声仍在主导画面，此时更适合观察谱带和主体轮廓。"
        if progress < 0.5:
            return "主体轮廓开始浮出，可以判断目标家族并准备出卡。"
        if progress < 0.8:
            return "局部细节正在显影，错误决策会明显拉高污染度。"
        return "终局判断阶段已到来，越稳妥分数越低，越冒险收益越高。"

    def _progression_snapshot(self, progress: PlayerCampaignProgress) -> ProgressSnapshot:
        items = [self._level_progress_item(level, progress) for level in self.levels]
        current_item = next(
            item for item in items if item.level_id == progress.current_level_id
        )
        return ProgressSnapshot(
            current_level_id=progress.current_level_id,
            highest_unlocked_level_id=progress.highest_unlocked_level_id,
            completed_level_ids=sorted(
                progress.completed_level_ids,
                key=lambda level_id: self.level_indices[level_id],
            ),
            completed_count=len(progress.completed_level_ids),
            total_levels=len(self.levels),
            campaign_complete=progress.campaign_complete,
            campaign_total_score=self._campaign_total_score(progress),
            best_scores_by_level=dict(progress.best_scores_by_level),
            current_level=current_item,
            levels=items,
        )

    def _level_progress_item(
        self,
        level_definition: LevelDefinition,
        progress: PlayerCampaignProgress,
    ) -> LevelProgressItem:
        highest_index = self.level_indices[progress.highest_unlocked_level_id]
        level_index = self.level_indices[level_definition.level_id]
        return LevelProgressItem(
            level_id=level_definition.level_id,
            chapter=level_definition.chapter,
            level=level_definition.level,
            chapter_title=level_definition.chapter_title,
            level_title=level_definition.level_title,
            mission_title=level_definition.mission_title,
            summary=level_definition.summary,
            max_guesses=level_definition.max_guesses,
            max_cards=level_definition.max_cards,
            candidate_count=level_definition.candidate_count,
            best_score=progress.best_scores_by_level.get(level_definition.level_id),
            is_current=level_definition.level_id == progress.current_level_id,
            is_completed=level_definition.level_id in progress.completed_level_ids,
            is_unlocked=level_index <= highest_index,
        )

    def _snapshot(self, session: Session) -> SessionSnapshot:
        progress = session.frame_index / max(session.total_frames - 1, 1)
        variant_key = self._resolve_variant_key(session)
        stability_value = round(session.stability)
        corruption_value = round(session.corruption)
        interval_ms = step_interval_ms(session.total_frames)
        return SessionSnapshot(
            session_id=session.session_id,
            level_id=session.level_id,
            rule_id=session.level_rule_id,
            chapter=session.chapter,
            level=session.level,
            chapter_title=session.chapter_title,
            level_title=session.level_title,
            level_summary=session.level_summary,
            rule_summary=session.rule_summary,
            rule_badges=list(session.rule_badges),
            score=session.score,
            combo=session.combo,
            status=session.status,
            frames_remaining=session.frames_remaining,
            seconds_remaining=round((session.frames_remaining * interval_ms) / 1000, 1),
            stability=stability_value,
            corruption=corruption_value,
            frame_index=session.frame_index,
            total_frames=session.total_frames,
            progress=round(progress, 4),
            image_url=self._frame_url(session, session.frame_index, variant_key),
            candidate_labels=self._visible_candidate_labels(session),
            masked_candidates=[
                label
                for label in self._visible_candidate_labels(session)
                if label == MASKED_CANDIDATE_LABEL
            ],
            remaining_guesses=session.remaining_guesses,
            max_guesses=session.max_guesses,
            cards_remaining=session.cards_remaining,
            max_cards=session.max_cards,
            disabled_card_ids=session.disabled_card_ids,  # type: ignore[arg-type]
            hint=session.hint,
            events=session.events,
            card_options=list(self.card_options),
            used_cards=session.used_cards,  # type: ignore[arg-type]
            revealed_target=session.revealed_target,
            phase_label=self._phase_label(session),
            objective_phase=session.objective_phase,  # type: ignore[arg-type]
            family_commit_required=self._requires_family_commit(session),
            committed_family=session.committed_family,  # type: ignore[arg-type]
            freeze_remaining=session.freeze_remaining,
            frozen_region=session.frozen_region,  # type: ignore[arg-type]
            rule_status=self._rule_status(session),
            mission_title=session.mission_title,
            threat_label=self._threat_label(corruption_value),
            step_interval_ms=interval_ms,
            score_breakdown=session.score_breakdown,
            score_events=session.score_events,
            loss_reason=session.loss_reason,
            ended_at=session.ended_at,
            awaiting_advancement=session.awaiting_advancement,
            next_level_id=session.next_level_id,
            next_level_title=session.next_level_title,
            next_level_summary=session.next_level_summary,
            campaign_complete=session.campaign_complete,
            level_best_score=session.level_best_score,
            level_best_improved=session.level_best_improved,
        )

    def _campaign_total_score(self, progress: PlayerCampaignProgress) -> int:
        return sum(progress.best_scores_by_level.values())

    def _update_level_best_score(
        self,
        progress: PlayerCampaignProgress,
        session: Session,
    ) -> None:
        previous_best = progress.best_scores_by_level.get(session.level_id)
        session.level_best_improved = previous_best is None or session.score > previous_best
        if session.level_best_improved:
            progress.best_scores_by_level[session.level_id] = session.score
        session.level_best_score = progress.best_scores_by_level.get(session.level_id, session.score)

    def _score_breakdown_model(self, breakdown: ScoreBreakdownData) -> ScoreBreakdown:
        return ScoreBreakdown(
            process_score_total=breakdown.process_score_total,
            base_score=breakdown.base_score,
            early_bonus=breakdown.early_bonus,
            time_bonus=breakdown.time_bonus,
            stability_bonus=breakdown.stability_bonus,
            low_corruption_bonus=breakdown.low_corruption_bonus,
            mission_bonus=breakdown.mission_bonus,
            card_penalty=breakdown.card_penalty,
            settlement_score=breakdown.settlement_score,
            final_score=breakdown.final_score,
        )

    def _card_score_detail(
        self,
        *,
        card_id: str,
        matched: bool,
        stability_delta: float,
        corruption_delta: float,
    ) -> str:
        stability_text = f"稳定 {'+' if stability_delta >= 0 else ''}{round(stability_delta)}"
        corruption_text = f"污染 {'+' if corruption_delta >= 0 else ''}{round(corruption_delta)}"
        if card_id == "sharpen-outline":
            return f"通用稳像。{stability_text}，{corruption_text}。"
        if matched:
            return f"命中目标家族。{stability_text}，{corruption_text}。"
        return f"未命中目标家族。{stability_text}，{corruption_text}，轨迹会偏向误导分支。"

    def _settlement_detail(self, breakdown: ScoreBreakdownData) -> str:
        return (
            f"基础 {breakdown.base_score}，提前识别 {breakdown.early_bonus}，剩余时间 "
            f"{breakdown.time_bonus}，稳定 {breakdown.stability_bonus}，低污染 "
            f"{breakdown.low_corruption_bonus}，任务 {breakdown.mission_bonus}，"
            f"卡牌惩罚 -{breakdown.card_penalty}。"
        )

    def _ended_at_iso(self) -> str:
        return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
            "+00:00", "Z"
        )

    def _frame_url(self, session: Session, frame_index: int, variant_key: str) -> str:
        token = self._frame_token(session, frame_index, variant_key)
        return f"/api/session/{session.session_id}/frames/{frame_index}?variant={variant_key}&token={token}"

    def _frame_token(self, session: Session, frame_index: int, variant_key: str) -> str:
        payload = f"{session.session_id}:{session.sample_id}:{frame_index}:{variant_key}".encode(
            "utf-8"
        )
        secret = session.frame_secret.encode("utf-8")
        return hmac.new(secret, payload, hashlib.sha256).hexdigest()

    def _resolve_variant_key(self, session: Session) -> str:
        variant_key = self._select_trajectory_variant(session)
        if variant_key in self.trajectory_store.variant_keys:
            return variant_key
        return "base"

    def _select_trajectory_variant(self, session: Session) -> str:
        if session.corruption >= GAME_CONFIG.presentation.corrupted_variant_threshold:
            return "corrupted"

        if session.frozen_region is not None:
            return f"freeze_{session.frozen_region.replace('-', '_')}"

        if "mechanical-lens" in session.used_cards and session.target.family in {
            "machine",
            "structure",
        }:
            return "focus_machine"

        if "bio-scan" in session.used_cards and session.target.family == "living":
            return "focus_living"

        if "mechanical-lens" in session.used_cards or "bio-scan" in session.used_cards:
            return "misguided"

        if "sharpen-outline" in session.used_cards:
            return "focus_generic"

        return "base"

    def _card_matches_target(self, session: Session, card_id: str) -> bool:
        if card_id == "mechanical-lens":
            return session.target.family in {"machine", "structure"}
        if card_id == "bio-scan":
            return session.target.family == "living"
        return True

    def _initialize_rule_state(self, session: Session) -> None:
        if session.level_rule_id in {"freeze-choice", "freeze-delay", "final-archive"}:
            session.freeze_remaining = 1
        if self._requires_family_commit(session):
            session.objective_phase = "classify"
        if session.level_rule_id in {"masked-candidates", "final-archive"}:
            session.hidden_candidate_indices = self._pick_masked_candidate_indices(session, count=2)
        if session.level_rule_id == "rotating-echo":
            session.rotating_echo_index = self._pick_rotating_echo_index(session)
            session.rotating_echo_pool = self._build_rotating_echo_pool(session)

    def _requires_family_commit(self, session: Session) -> bool:
        return session.level_rule_id in {
            "family-commit",
            "dual-phase-identification",
            "final-archive",
        }

    def _card_blocked(self, session: Session, card_id: str) -> bool:
        return (
            session.cards_remaining <= 0
            or card_id in session.disabled_card_ids
            or card_id in session.used_cards
        )

    def _step_rule_adjustments(self, session: Session) -> tuple[float, float]:
        extra_stability_delta = 0.0
        extra_corruption_delta = 0.0
        if session.level_rule_id == "noise-budget" and session.step_streak > 1:
            extra_corruption_delta += 4 + (session.step_streak - 2) * 2
        if session.freeze_step_tax_pending:
            session.frames_remaining = max(0, session.frames_remaining - 1)
            extra_corruption_delta += 6
            session.freeze_step_tax_pending = False
            self._append_event(session, "冻结延迟生效：本次推进额外消耗了解码窗口。")
        return extra_stability_delta, extra_corruption_delta

    def _apply_progression_rule_updates(self, session: Session) -> None:
        if session.level_rule_id in {"masked-candidates", "final-archive"}:
            self._reveal_hidden_candidate(session)
        if session.level_rule_id == "rotating-echo":
            self._rotate_echo_candidate(session)

    def _apply_threshold_rule_updates(self, session: Session) -> None:
        if session.level_rule_id != "corruption-reorder":
            return
        if session.threshold_triggered or session.corruption < 50:
            return
        session.threshold_triggered = True
        rng = random.Random(f"{session.session_id}:threshold")
        rng.shuffle(session.candidate_labels)
        disabled_card = next(
            (
                card_id
                for card_id in CARD_DISABLE_PRIORITY
                if card_id not in session.disabled_card_ids and card_id not in session.used_cards
            ),
            None,
        )
        if disabled_card is not None:
            session.disabled_card_ids.append(disabled_card)
        self._append_event(session, "污染跨过阈值：候选顺序被打乱，工具许可也被改写。")

    def _apply_post_card_rule_updates(self, session: Session, *, card_id: str, matched: bool) -> None:
        if session.level_rule_id == "family-commit" and session.committed_family == session.target.family:
            if card_id in {"mechanical-lens", "bio-scan"} and matched:
                session.score += 4
                self._shift_risk(session, stability_delta=2, corruption_delta=-2)
                self._append_event(session, "承诺与卡牌共振一致，读数额外稳定。")
        if session.level_rule_id == "single-card-contract":
            session.disabled_card_ids.extend(
                other_id
                for other_id in CARD_DEFINITIONS
                if other_id != card_id and other_id not in session.disabled_card_ids
            )
            self._append_event(session, f"契约生效：{CARD_DEFINITIONS[card_id].title} 成为本局唯一授权工具。")
        if session.level_rule_id == "evidence-debt":
            session.evidence_debt += 18
            self._append_event(session, f"证据债务累积：当前结算债务 -{session.evidence_debt}。")

    def _apply_settlement_rule_adjustments(
        self,
        session: Session,
        breakdown: ScoreBreakdownData,
    ) -> ScoreBreakdownData:
        if session.level_rule_id != "evidence-debt":
            return breakdown
        if session.evidence_debt <= 0 or round(session.corruption) <= 40:
            return breakdown
        return ScoreBreakdownData(
            process_score_total=breakdown.process_score_total,
            base_score=breakdown.base_score,
            early_bonus=breakdown.early_bonus,
            time_bonus=breakdown.time_bonus,
            stability_bonus=breakdown.stability_bonus,
            low_corruption_bonus=breakdown.low_corruption_bonus,
            mission_bonus=breakdown.mission_bonus,
            card_penalty=breakdown.card_penalty + session.evidence_debt,
            settlement_score=breakdown.settlement_score - session.evidence_debt,
            final_score=breakdown.final_score - session.evidence_debt,
        )

    def _append_rule_settlement_events(self, session: Session) -> None:
        if session.level_rule_id != "evidence-debt" or session.evidence_debt <= 0:
            return
        if round(session.corruption) <= 40:
            self._append_score_event(
                session,
                kind="rule",
                title="证据债务豁免",
                delta=0,
                detail="以低污染完成识别，本局证据债务被全部豁免。",
            )
            return
        self._append_score_event(
            session,
            kind="rule",
            title="证据债务",
            delta=-session.evidence_debt,
            detail=f"高污染完成识别，结算额外扣除 {session.evidence_debt} 分。",
        )

    def _visible_candidate_labels(self, session: Session) -> list[str]:
        return [
            MASKED_CANDIDATE_LABEL if index in session.hidden_candidate_indices else label
            for index, label in enumerate(session.candidate_labels)
        ]

    def _guessable_labels(self, session: Session) -> list[str]:
        return [
            label
            for index, label in enumerate(session.candidate_labels)
            if index not in session.hidden_candidate_indices
        ]

    def _pick_masked_candidate_indices(self, session: Session, *, count: int) -> set[int]:
        candidate_indices = [
            index
            for index, label in enumerate(session.candidate_labels)
            if label != session.target.label
        ]
        rng = random.Random(f"{session.session_id}:mask")
        rng.shuffle(candidate_indices)
        return set(candidate_indices[:count])

    def _reveal_hidden_candidate(self, session: Session) -> None:
        if not session.hidden_candidate_indices:
            return
        next_index = sorted(session.hidden_candidate_indices)[0]
        session.hidden_candidate_indices.remove(next_index)
        self._append_event(session, f"新线索解锁：候选槽位显露为 {session.candidate_labels[next_index]}。")

    def _pick_rotating_echo_index(self, session: Session) -> int | None:
        for index, label in enumerate(session.candidate_labels):
            if label != session.target.label:
                return index
        return None

    def _build_rotating_echo_pool(self, session: Session) -> list[str]:
        target_pool = level_by_id(session.level_id).target_pool
        return [
            label
            for label in target_pool
            if label != session.target.label and label not in session.candidate_labels
        ]

    def _rotate_echo_candidate(self, session: Session) -> None:
        if session.rotating_echo_index is None or not session.rotating_echo_pool:
            return
        current_label = session.candidate_labels[session.rotating_echo_index]
        replacement = session.rotating_echo_pool.pop(0)
        session.candidate_labels[session.rotating_echo_index] = replacement
        session.rotating_echo_pool.append(current_label)
        self._append_event(session, f"回声诱饵变化：一条候选信号已替换为 {replacement}。")

    def _rule_status(self, session: Session) -> str | None:
        if session.level_rule_id == "final-archive":
            family_text = (
                "等待家族判定"
                if session.committed_family is None
                else f"已判定 {FAMILY_LABELS[session.committed_family]}"
            )
            freeze_text = (
                "未冻结"
                if session.frozen_region is None
                else f"已冻结 {FREEZE_REGION_DEFINITIONS[session.frozen_region].title}"
            )
            hidden = len(session.hidden_candidate_indices)
            return f"{family_text} / {freeze_text} / 已揭示 {len(session.candidate_labels) - hidden}/{len(session.candidate_labels)} 候选。"
        if self._requires_family_commit(session):
            if session.committed_family is None:
                return "当前阶段：先完成目标家族判定。"
            return f"已承诺家族：{FAMILY_LABELS[session.committed_family]}。"
        if session.level_rule_id in {"freeze-choice", "freeze-delay"}:
            if session.frozen_region is None:
                return f"冻结次数：{session.freeze_remaining}/1。"
            return f"已冻结区域：{FREEZE_REGION_DEFINITIONS[session.frozen_region].title}。"
        if session.level_rule_id in {"masked-candidates", "final-archive"}:
            hidden = len(session.hidden_candidate_indices)
            revealed = len(session.candidate_labels) - hidden
            return f"候选揭示进度：{revealed}/{len(session.candidate_labels)}。"
        if session.level_rule_id == "rotating-echo":
            return "阶段点会替换 1 个诱饵候选。"
        if session.level_rule_id == "single-card-contract":
            if not session.used_cards:
                return "首次用卡将锁定本局唯一工具。"
            return f"契约卡：{CARD_DEFINITIONS[session.used_cards[0]].title}。"
        if session.level_rule_id == "noise-budget":
            return f"连续推进计数：{session.step_streak}。连续推进越多，额外污染越高。"
        if session.level_rule_id == "corruption-reorder":
            if session.threshold_triggered:
                return "污染阈值已触发：候选已重排。"
            return "污染达到 50 后会触发候选重排和工具禁用。"
        if session.level_rule_id == "evidence-debt":
            return f"当前证据债务：-{session.evidence_debt}。低污染完成可豁免。"
        return None

    def _phase_label(self, session: Session) -> str:
        progress = session.frame_index / max(session.total_frames - 1, 1)
        return phase_label(progress=progress, corruption=round(session.corruption))

    def _threat_label(self, corruption: int) -> str:
        return threat_label(corruption)

    def _prune_expired_sessions(self) -> None:
        now = self.clock()
        expired_session_ids = [
            session_id
            for session_id, session in self.sessions.items()
            if now - session.last_touched_at > SESSION_TTL_SECONDS
        ]
        for session_id in expired_session_ids:
            del self.sessions[session_id]

    def _normalize_player_id(self, player_id: str | None) -> str:
        if player_id is None:
            return "anonymous"
        normalized = player_id.strip()
        if not normalized:
            return "anonymous"
        if is_user_actor(normalized):
            return normalized
        if normalized.startswith("anon:"):
            suffix = normalized.split(":", 1)[1].strip()
            return f"anon:{(suffix or 'anonymous')[:64]}"
        return normalized[:64]

    def _validate_level_definitions(self) -> None:
        if len(self.levels) != GAME_CONFIG.campaign.chapters * GAME_CONFIG.campaign.levels_per_chapter:
            raise ValueError("关卡配置数量与章节结构不一致。")

        for level_definition in LEVEL_DEFINITIONS:
            if level_definition.level_id not in self.level_indices:
                raise ValueError(f"未知关卡标识：{level_definition.level_id}")
            if len(level_definition.target_pool) < level_definition.candidate_count:
                raise ValueError(f"{level_definition.level_id} 的目标池不足以生成候选列表。")
            missing_labels = [
                label for label in level_definition.target_pool if label not in self.targets_by_label
            ]
            if missing_labels:
                missing = "、".join(missing_labels)
                raise ValueError(f"{level_definition.level_id} 缺少目标素材：{missing}")
            if level_definition.max_guesses <= 0 or level_definition.max_cards <= 0:
                raise ValueError(f"{level_definition.level_id} 的资源配置无效。")
