from __future__ import annotations

import random
import uuid
from dataclasses import dataclass, field

from .game_data import (
    CARD_DEFINITIONS,
    FREEZE_REGION_LABELS,
    TARGETS,
    TargetDefinition,
)
from .schemas import SessionSnapshot
from .trajectory_store import TrajectoryStore


STEP_INTERVAL_MS = 900
MAX_GUESSES = 3
MAX_CARDS = 2


@dataclass
class Session:
    session_id: str
    chapter: int
    level: int
    target: TargetDefinition
    candidate_labels: list[str]
    score: int = 0
    combo: int = 0
    status: str = "playing"
    time_remaining: int = 0
    frame_index: int = 0
    total_frames: int = 0
    remaining_guesses: int = MAX_GUESSES
    cards_remaining: int = MAX_CARDS
    freeze_available: bool = True
    hint: str = ""
    events: list[str] = field(default_factory=list)
    used_cards: list[str] = field(default_factory=list)
    frozen_region: str | None = None
    revealed_target: str | None = None


class GameService:
    def __init__(self, trajectory_store: TrajectoryStore | None = None) -> None:
        self.trajectory_store = trajectory_store or TrajectoryStore()
        self.sessions: dict[str, Session] = {}
        self.round_counter = 0

    def start_session(self) -> SessionSnapshot:
        self.round_counter += 1
        rng = random.Random()

        target = rng.choice(TARGETS)
        distractors = [candidate.label for candidate in TARGETS if candidate != target]
        candidate_labels = rng.sample(distractors, k=5)
        candidate_labels.append(target.label)
        rng.shuffle(candidate_labels)

        chapter = min(3, ((self.round_counter - 1) // 8) + 1)
        level = ((self.round_counter - 1) % 8) + 1
        session_id = uuid.uuid4().hex[:8]
        total_frames = self.trajectory_store.total_frames

        session = Session(
            session_id=session_id,
            chapter=chapter,
            level=level,
            target=target,
            candidate_labels=candidate_labels,
            time_remaining=total_frames,
            total_frames=total_frames,
            hint=target.hint,
            events=[
                "信号已锁定，遗物从原始噪声中开始显形。",
                f"分类提示：{target.hint}。",
            ],
        )
        self.sessions[session_id] = session
        return self._snapshot(session)

    def step(self, session_id: str) -> SessionSnapshot:
        session = self._get_session(session_id)
        if session.status != "playing":
            return self._snapshot(session)

        session.frame_index = min(session.total_frames - 1, session.frame_index + 1)
        session.time_remaining = max(0, session.time_remaining - 1)

        if session.frame_index in {4, 9, 14, 19}:
            self._append_event(session, self._progress_message(session))

        if session.frame_index >= session.total_frames - 1 or session.time_remaining <= 0:
            session.status = "lost"
            session.revealed_target = session.target.label
            self._append_event(
                session,
                f"解码失败，隐藏目标是：{session.target.label}。",
            )

        return self._snapshot(session)

    def guess(self, session_id: str, label: str) -> SessionSnapshot:
        session = self._get_session(session_id)
        if session.status != "playing":
            return self._snapshot(session)

        guess = label.strip().lower()
        if guess == session.target.label:
            progress = session.frame_index / max(session.total_frames - 1, 1)
            early_bonus = int((1 - progress) * 80)
            time_bonus = session.time_remaining * 5
            precision_bonus = session.remaining_guesses * 10
            tool_penalty = len(session.used_cards) * 10
            if session.frozen_region is not None:
                tool_penalty += 15

            session.score += 100 + early_bonus + time_bonus + precision_bonus - tool_penalty
            session.combo += 1
            session.status = "won"
            session.revealed_target = session.target.label
            self._append_event(
                session,
                f"识别正确，遗物确认为：{session.target.label}。",
            )
            return self._snapshot(session)

        session.remaining_guesses = max(0, session.remaining_guesses - 1)
        session.score = max(0, session.score - 20)
        self._append_event(session, f"猜测错误：{guess}。信号再次变得不稳定。")

        if session.remaining_guesses == 0:
            session.status = "lost"
            session.revealed_target = session.target.label
            self._append_event(
                session,
                f"猜测次数耗尽，隐藏目标是：{session.target.label}。",
            )

        return self._snapshot(session)

    def use_card(self, session_id: str, card_id: str) -> SessionSnapshot:
        session = self._get_session(session_id)
        if session.status != "playing":
            return self._snapshot(session)
        if card_id not in CARD_DEFINITIONS:
            raise ValueError("未知卡牌。")
        if session.cards_remaining <= 0 or card_id in session.used_cards:
            return self._snapshot(session)

        session.used_cards.append(card_id)
        session.cards_remaining -= 1
        definition = CARD_DEFINITIONS[card_id]
        self._append_event(session, f"已使用卡牌：{definition.title}。{definition.summary}")
        return self._snapshot(session)

    def freeze(self, session_id: str, region: str) -> SessionSnapshot:
        session = self._get_session(session_id)
        if session.status != "playing":
            return self._snapshot(session)
        if region not in FREEZE_REGION_LABELS:
            raise ValueError("未知冻结区域。")
        if not session.freeze_available:
            return self._snapshot(session)

        session.freeze_available = False
        session.frozen_region = region
        self._append_event(session, f"区域已锁定：{FREEZE_REGION_LABELS[region]}。")
        return self._snapshot(session)

    def _get_session(self, session_id: str) -> Session:
        if session_id not in self.sessions:
            raise KeyError("未找到该局游戏。")
        return self.sessions[session_id]

    def _append_event(self, session: Session, message: str) -> None:
        session.events.append(message)
        if len(session.events) > 7:
            session.events = session.events[-7:]

    def _progress_message(self, session: Session) -> str:
        progress = session.frame_index / max(session.total_frames - 1, 1)
        if progress < 0.35:
            return "轮廓仍不稳定，噪声依旧占主导。"
        if progress < 0.65:
            return "主体轮廓开始出现，可以逐步排除错误候选。"
        if progress < 0.85:
            return "次级细节已可见，抢答窗口正在打开。"
        return "信号接近完成，现在更稳，但得分会更低。"

    def _snapshot(self, session: Session) -> SessionSnapshot:
        progress = session.frame_index / max(session.total_frames - 1, 1)
        return SessionSnapshot(
            session_id=session.session_id,
            chapter=session.chapter,
            level=session.level,
            score=session.score,
            combo=session.combo,
            status=session.status,
            time_remaining=session.time_remaining,
            frame_index=session.frame_index,
            total_frames=session.total_frames,
            progress=round(progress, 4),
            image_data=self.trajectory_store.get_frame(
                target_label=session.target.label,
                variant_key=self._select_trajectory_variant(session),
                frame_index=session.frame_index,
            ),
            candidate_labels=session.candidate_labels,
            remaining_guesses=session.remaining_guesses,
            cards_remaining=session.cards_remaining,
            freeze_available=session.freeze_available,
            hint=session.hint,
            events=session.events,
            used_cards=session.used_cards,  # type: ignore[arg-type]
            frozen_region=session.frozen_region,  # type: ignore[arg-type]
            revealed_target=session.revealed_target,
            step_interval_ms=STEP_INTERVAL_MS,
        )

    def _select_trajectory_variant(self, session: Session) -> str:
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
