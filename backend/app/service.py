from __future__ import annotations

import hashlib
import hmac
import random
import time
import uuid
from dataclasses import dataclass, field
from threading import RLock
from typing import Callable

from .frame_renderer import DEFAULT_TOTAL_FRAMES
from .gameplay_config import (
    GAME_CONFIG,
    MissionType,
    calculate_win_score,
    card_effect,
    chapter_and_level_for_round,
    high_corruption_event_frames,
    mission_for_round,
    phase_label,
    progress_event_frames,
    pulse_frame_cost,
    step_interval_ms,
    step_risk,
    threat_label,
)
from .game_data import (
    CARD_DEFINITIONS,
    FREEZE_REGION_DEFINITIONS,
    FREEZE_REGION_LABELS,
    TARGETS,
    TargetDefinition,
)
from .schemas import CardOption, FreezeRegionOption, SessionSnapshot
from .trajectory_store import FrameAsset, TrajectoryStore


SESSION_TTL_SECONDS = GAME_CONFIG.presentation.session_ttl_seconds
MAX_GUESSES = GAME_CONFIG.resources.max_guesses
MAX_CARDS = GAME_CONFIG.resources.max_cards
MAX_SCAN_CHARGES = GAME_CONFIG.resources.max_scan_charges
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
    scan_charges: int = MAX_SCAN_CHARGES
    frame_index: int = 0
    total_frames: int = DEFAULT_TOTAL_FRAMES
    remaining_guesses: int = MAX_GUESSES
    cards_remaining: int = MAX_CARDS
    freeze_available: bool = True
    hint: str = ""
    signature_clue: str | None = None
    signature_revealed: bool = False
    events: list[str] = field(default_factory=list)
    used_cards: list[str] = field(default_factory=list)
    frozen_region: str | None = None
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
        self.freeze_region_options = tuple(
            FreezeRegionOption(
                id=region,
                title=definition.title,
                summary=definition.summary,
            )
            for region, definition in FREEZE_REGION_DEFINITIONS.items()
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
                signature_clue=target.signature,
                events=[
                    "信号已锁定，遗物从原始噪声中开始显形。",
                    f"分类提示：{target.hint}。",
                    f"当前任务：{mission.title}。",
                    "脉冲扫描已就绪，可用来缩小候选范围。",
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
                session.score += calculate_win_score(
                    session.mission_type,
                    progress=progress,
                    frames_remaining=session.frames_remaining,
                    total_frames=session.total_frames,
                    stability=round(session.stability),
                    corruption=round(session.corruption),
                    cards_remaining=session.cards_remaining,
                    freeze_available=session.freeze_available,
                    scan_charges=session.scan_charges,
                    remaining_guesses=session.remaining_guesses,
                )
                session.combo = self._record_win(session.player_id)
                session.status = "won"
                session.revealed_target = session.target.label
                self._append_event(
                    session,
                    f"识别正确，遗物确认为：{session.target.label}。",
                )
                return self._snapshot(session)

            session.remaining_guesses = max(0, session.remaining_guesses - 1)
            session.score = max(0, session.score + GAME_CONFIG.actions.wrong_guess.score)
            self._shift_risk(
                session,
                stability_delta=GAME_CONFIG.actions.wrong_guess.stability,
                corruption_delta=GAME_CONFIG.actions.wrong_guess.corruption,
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

            self._resolve_if_failed(session)
            return self._snapshot(session)

    def freeze(self, player_id: str | None, session_id: str, region: str) -> SessionSnapshot:
        with self._lock:
            session = self._get_session(player_id, session_id)
            if session.status != "playing":
                return self._snapshot(session)
            if region not in FREEZE_REGION_LABELS:
                raise ValueError("未知冻结区域。")
            if not session.freeze_available:
                return self._snapshot(session)

            session.freeze_available = False
            session.frozen_region = region
            self._shift_risk(
                session,
                stability_delta=GAME_CONFIG.actions.freeze.stability,
                corruption_delta=GAME_CONFIG.actions.freeze.corruption,
            )
            self._append_event(
                session,
                f"区域已锁定：{FREEZE_REGION_LABELS[region]}。局部稳定度提升，但整体污染略有上升。",
            )
            self._resolve_if_failed(session)
            return self._snapshot(session)

    def pulse_scan(self, player_id: str | None, session_id: str) -> SessionSnapshot:
        with self._lock:
            session = self._get_session(player_id, session_id)
            if session.status != "playing":
                return self._snapshot(session)
            if session.scan_charges <= 0:
                return self._snapshot(session)

            session.scan_charges -= 1
            session.signature_revealed = True
            session.frames_remaining = max(
                0,
                session.frames_remaining - pulse_frame_cost(session.total_frames),
            )
            self._shift_risk(
                session,
                stability_delta=GAME_CONFIG.actions.pulse_scan.stability,
                corruption_delta=GAME_CONFIG.actions.pulse_scan.corruption,
            )
            session.candidate_labels = self._narrow_candidates(session)
            self._append_event(
                session,
                f"脉冲扫描捕获特征线索：{session.signature_clue}。候选范围已收缩。",
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
        session.revealed_target = session.target.label
        self._append_event(session, f"{reason} 隐藏目标是：{session.target.label}。")

    def _progress_message(self, session: Session) -> str:
        progress = session.frame_index / max(session.total_frames - 1, 1)
        if progress < 0.25:
            return "噪声仍在主导画面，此时更适合收集风险和特征信息。"
        if progress < 0.5:
            return "主体轮廓开始浮出，可以考虑为后续抢答铺垫。"
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
            scan_charges=session.scan_charges,
            frame_index=session.frame_index,
            total_frames=session.total_frames,
            progress=round(progress, 4),
            image_url=self._frame_url(session, session.frame_index, variant_key),
            candidate_labels=session.candidate_labels,
            remaining_guesses=session.remaining_guesses,
            cards_remaining=session.cards_remaining,
            freeze_available=session.freeze_available,
            hint=session.hint,
            events=session.events,
            card_options=list(self.card_options),
            freeze_region_options=list(self.freeze_region_options),
            used_cards=session.used_cards,  # type: ignore[arg-type]
            frozen_region=session.frozen_region,  # type: ignore[arg-type]
            revealed_target=session.revealed_target,
            signature_clue=session.signature_clue if session.signature_revealed else None,
            signature_revealed=session.signature_revealed,
            phase_label=self._phase_label(session),
            mission_title=session.mission_title,
            threat_label=self._threat_label(corruption_value),
            step_interval_ms=interval_ms,
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

        if session.signature_revealed:
            return "pulse_reveal"

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

    def _narrow_candidates(self, session: Session) -> list[str]:
        if len(session.candidate_labels) <= 4:
            return session.candidate_labels

        rng = random.Random(f"{session.session_id}:pulse")
        distractors = [label for label in session.candidate_labels if label != session.target.label]
        trimmed = rng.sample(distractors, k=3)
        narrowed = [session.target.label, *trimmed]
        rng.shuffle(narrowed)
        return narrowed

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
