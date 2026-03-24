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

from .frame_renderer import DEFAULT_TOTAL_FRAMES
from .gameplay_config import (
    GAME_CONFIG,
    MissionType,
    ScoreBreakdownData,
    calculate_loss_breakdown,
    calculate_score_breakdown,
    card_effect,
    chapter_and_level_for_round,
    high_corruption_event_frames,
    mission_for_round,
    phase_label,
    progress_event_frames,
    step_interval_ms,
    step_risk,
    threat_label,
)
from .game_data import (
    CARD_DEFINITIONS,
    TARGETS,
    TargetDefinition,
)
from .schemas import CardOption, ScoreBreakdown, ScoreEvent, SessionSnapshot
from .trajectory_store import FrameAsset, TrajectoryStore


SESSION_TTL_SECONDS = GAME_CONFIG.presentation.session_ttl_seconds
MAX_GUESSES = GAME_CONFIG.resources.max_guesses
MAX_CARDS = GAME_CONFIG.resources.max_cards
MAX_STABILITY = GAME_CONFIG.resources.max_stability
MAX_CORRUPTION = GAME_CONFIG.resources.max_corruption


@dataclass
class Session:
    session_id: str
    player_id: str
    frame_secret: str
    sample_id: str
    chapter: int
    level: int
    mission_type: MissionType
    mission_title: str
    target: TargetDefinition
    candidate_labels: list[str]
    score: int = 0
    combo: int = 0
    status: str = "playing"
    frames_remaining: int = 0
    stability: float = 0.0
    corruption: float = 0.0
    frame_index: int = 0
    total_frames: int = DEFAULT_TOTAL_FRAMES
    remaining_guesses: int = MAX_GUESSES
    cards_remaining: int = MAX_CARDS
    hint: str = ""
    events: list[str] = field(default_factory=list)
    used_cards: list[str] = field(default_factory=list)
    score_events: list[ScoreEvent] = field(default_factory=list)
    score_breakdown: ScoreBreakdown | None = None
    loss_reason: str | None = None
    ended_at: str | None = None
    revealed_target: str | None = None
    last_touched_at: float = field(default_factory=time.monotonic)


@dataclass
class PlayerProgress:
    rounds_started: int = 0
    streak: int = 0


class GameService:
    def __init__(
        self,
        trajectory_store: TrajectoryStore | None = None,
        *,
        clock: Callable[[], float] | None = None,
    ) -> None:
        self.trajectory_store = trajectory_store or TrajectoryStore()
        self.clock = clock or time.monotonic
        self.sessions: dict[str, Session] = {}
        self.player_progress: dict[str, PlayerProgress] = {}
        self.targets = tuple(
            target for target in TARGETS if self.trajectory_store.has_target(target.label)
        )
        self.card_options = tuple(
            CardOption(
                id=card_id,
                title=definition.title,
                summary=definition.summary,
            )
            for card_id, definition in CARD_DEFINITIONS.items()
        )
        self._lock = RLock()
        if not self.targets:
            raise ValueError("轨迹清单中没有可用目标。")
        if len(self.targets) < 6:
            raise ValueError("轨迹清单中的可用目标不足 6 个，无法生成候选列表。")

    def start_session(self, player_id: str | None) -> SessionSnapshot:
        player_key = self._normalize_player_id(player_id)
        with self._lock:
            self._prune_expired_sessions()
            progress = self.player_progress.setdefault(player_key, PlayerProgress())
            progress.rounds_started += 1

            rng = random.Random()
            target = rng.choice(self.targets)
            distractors = [candidate.label for candidate in self.targets if candidate != target]
            candidate_labels = rng.sample(distractors, k=5)
            candidate_labels.append(target.label)
            rng.shuffle(candidate_labels)

            mission = mission_for_round(progress.rounds_started)
            chapter, level = chapter_and_level_for_round(progress.rounds_started)
            session_id = uuid.uuid4().hex
            total_frames = self.trajectory_store.total_frames
            sample_id = rng.choice(self.trajectory_store.sample_ids_for_target(target.label))

            session = Session(
                session_id=session_id,
                player_id=player_key,
                frame_secret=uuid.uuid4().hex,
                sample_id=sample_id,
                chapter=chapter,
                level=level,
                mission_type=mission.mission_type,
                mission_title=mission.title,
                target=target,
                candidate_labels=candidate_labels,
                combo=progress.streak,
                frames_remaining=max(total_frames - 1, 0),
                stability=GAME_CONFIG.initial_session.stability,
                corruption=GAME_CONFIG.initial_session.corruption,
                total_frames=total_frames,
                hint=target.hint,
                events=[
                    "信号已锁定，遗物从原始噪声中开始显形。",
                    f"分类提示：{target.hint}。",
                    f"当前任务：{mission.title}。",
                    "引导卡已装填。先判断目标家族，再决定是否出手。",
                ],
                last_touched_at=self.clock(),
            )
            self.sessions[session_id] = session
            return self._snapshot(session)

    def step(self, player_id: str | None, session_id: str) -> SessionSnapshot:
        with self._lock:
            session = self._get_session(player_id, session_id)
            if session.status != "playing":
                return self._snapshot(session)

            session.frame_index = min(session.total_frames - 1, session.frame_index + 1)
            session.frames_remaining = max(0, session.frames_remaining - 1)
            step_delta = step_risk(session.total_frames)
            self._shift_risk(
                session,
                stability_delta=step_delta.stability,
                corruption_delta=step_delta.corruption,
            )

            if session.frame_index in progress_event_frames(session.total_frames):
                self._append_event(session, self._progress_message(session))

            if (
                session.corruption >= GAME_CONFIG.presentation.corrupted_variant_threshold
                and session.frame_index in high_corruption_event_frames(session.total_frames)
            ):
                self._append_event(session, "污染度过高，画面开始出现伪轮廓和裂缝。")

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
            if guess not in session.candidate_labels:
                raise ValueError("猜测必须来自当前候选列表。")

            if guess == session.target.label:
                progress = session.frame_index / max(session.total_frames - 1, 1)
                breakdown = calculate_score_breakdown(
                    session.mission_type,
                    progress=progress,
                    frames_remaining=session.frames_remaining,
                    total_frames=session.total_frames,
                    stability=round(session.stability),
                    corruption=round(session.corruption),
                    cards_remaining=session.cards_remaining,
                    process_score_total=session.score,
                )
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
                self._append_event(
                    session,
                    f"识别正确，遗物确认为：{session.target.label}。",
                )
                return self._snapshot(session)

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
            if session.cards_remaining <= 0 or card_id in session.used_cards:
                return self._snapshot(session)

            session.used_cards.append(card_id)
            session.cards_remaining -= 1
            definition = CARD_DEFINITIONS[card_id]
            matched = self._card_matches_target(session, card_id)
            effect = card_effect(card_id, matched=matched)

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

    def _get_session(self, player_id: str | None, session_id: str) -> Session:
        self._prune_expired_sessions()
        player_key = self._normalize_player_id(player_id)
        session = self.sessions.get(session_id)
        if session is None or session.player_id != player_key:
            raise KeyError("未找到该局游戏。")

        session.last_touched_at = self.clock()
        return session

    def _progress_for(self, player_id: str | None) -> PlayerProgress:
        player_key = self._normalize_player_id(player_id)
        return self.player_progress.setdefault(player_key, PlayerProgress())

    def _record_win(self, player_id: str | None) -> int:
        progress = self._progress_for(player_id)
        progress.streak += 1
        return progress.streak

    def _record_loss(self, player_id: str | None) -> None:
        progress = self._progress_for(player_id)
        progress.streak = 0

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
        session.ended_at = self._ended_at_iso()
        session.revealed_target = session.target.label
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

    def _snapshot(self, session: Session) -> SessionSnapshot:
        progress = session.frame_index / max(session.total_frames - 1, 1)
        variant_key = self._resolve_variant_key(session)
        stability_value = round(session.stability)
        corruption_value = round(session.corruption)
        interval_ms = step_interval_ms(session.total_frames)
        return SessionSnapshot(
            session_id=session.session_id,
            chapter=session.chapter,
            level=session.level,
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
            candidate_labels=session.candidate_labels,
            remaining_guesses=session.remaining_guesses,
            cards_remaining=session.cards_remaining,
            hint=session.hint,
            events=session.events,
            card_options=list(self.card_options),
            used_cards=session.used_cards,  # type: ignore[arg-type]
            revealed_target=session.revealed_target,
            phase_label=self._phase_label(session),
            mission_title=session.mission_title,
            threat_label=self._threat_label(corruption_value),
            step_interval_ms=interval_ms,
            score_breakdown=session.score_breakdown,
            score_events=session.score_events,
            loss_reason=session.loss_reason,
            ended_at=session.ended_at,
        )

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
        return normalized[:64]
