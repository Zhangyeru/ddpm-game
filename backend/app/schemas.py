from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


CardId = Literal["sharpen-outline", "mechanical-lens", "bio-scan"]
GameStatus = Literal["playing", "won", "lost"]
ScoreEventKind = Literal["card", "guess_penalty", "settlement", "loss"]


class GuessRequest(BaseModel):
    label: str


class UseCardRequest(BaseModel):
    card_id: CardId


class CardOption(BaseModel):
    id: CardId
    title: str
    summary: str


class ScoreBreakdown(BaseModel):
    process_score_total: int
    base_score: int
    early_bonus: int
    time_bonus: int
    stability_bonus: int
    low_corruption_bonus: int
    mission_bonus: int
    card_penalty: int
    settlement_score: int
    final_score: int


class ScoreEvent(BaseModel):
    kind: ScoreEventKind
    title: str
    delta: int
    running_score: int
    detail: str


class SessionSnapshot(BaseModel):
    session_id: str
    chapter: int
    level: int
    score: int
    combo: int
    status: GameStatus
    frames_remaining: int
    seconds_remaining: float
    stability: int
    corruption: int
    frame_index: int
    total_frames: int
    progress: float
    image_url: str
    candidate_labels: list[str]
    remaining_guesses: int
    cards_remaining: int
    hint: str
    events: list[str]
    card_options: list[CardOption]
    used_cards: list[CardId]
    revealed_target: str | None
    phase_label: str
    mission_title: str
    threat_label: str
    step_interval_ms: int
    score_breakdown: ScoreBreakdown | None
    score_events: list[ScoreEvent]
    loss_reason: str | None
    ended_at: str | None
