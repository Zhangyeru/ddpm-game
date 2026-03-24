from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


CardId = Literal["sharpen-outline", "mechanical-lens", "bio-scan"]
TargetFamily = Literal["living", "machine", "structure"]
FreezeRegionId = Literal["upper-left", "center", "lower-right"]
GameStatus = Literal["playing", "won", "lost"]
ScoreEventKind = Literal["card", "guess_penalty", "settlement", "loss", "rule"]


class GuessRequest(BaseModel):
    label: str


class RegisterRequest(BaseModel):
    username: str
    password: str


class LoginRequest(BaseModel):
    username: str
    password: str


class UseCardRequest(BaseModel):
    card_id: CardId


class FreezeRequest(BaseModel):
    region: FreezeRegionId


class CommitFamilyRequest(BaseModel):
    family: TargetFamily


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


class LevelProgressItem(BaseModel):
    level_id: str
    chapter: int
    level: int
    chapter_title: str
    level_title: str
    mission_title: str
    summary: str
    max_guesses: int
    max_cards: int
    candidate_count: int
    best_score: int | None
    is_current: bool
    is_completed: bool
    is_unlocked: bool


class ProgressSnapshot(BaseModel):
    current_level_id: str
    highest_unlocked_level_id: str
    completed_level_ids: list[str]
    completed_count: int
    total_levels: int
    campaign_complete: bool
    campaign_total_score: int
    best_scores_by_level: dict[str, int]
    current_level: LevelProgressItem
    levels: list[LevelProgressItem]


class AuthUser(BaseModel):
    id: str
    username: str


class LeaderboardEntry(BaseModel):
    rank: int
    user_id: str
    username: str
    campaign_total_score: int
    completed_count: int
    campaign_complete: bool


class AuthResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"]
    user: AuthUser
    progression: ProgressSnapshot


class AuthSessionSnapshot(BaseModel):
    user: AuthUser
    progression: ProgressSnapshot


class SessionSnapshot(BaseModel):
    session_id: str
    level_id: str
    rule_id: str
    chapter: int
    level: int
    chapter_title: str
    level_title: str
    level_summary: str
    rule_summary: str
    rule_badges: list[str]
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
    masked_candidates: list[str]
    remaining_guesses: int
    max_guesses: int
    cards_remaining: int
    max_cards: int
    disabled_card_ids: list[CardId]
    hint: str
    events: list[str]
    card_options: list[CardOption]
    used_cards: list[CardId]
    revealed_target: str | None
    phase_label: str
    objective_phase: Literal["standard", "classify", "identify"]
    family_commit_required: bool
    committed_family: TargetFamily | None
    freeze_remaining: int
    frozen_region: FreezeRegionId | None
    rule_status: str | None
    mission_title: str
    threat_label: str
    step_interval_ms: int
    score_breakdown: ScoreBreakdown | None
    score_events: list[ScoreEvent]
    loss_reason: str | None
    ended_at: str | None
    awaiting_advancement: bool
    next_level_id: str | None
    next_level_title: str | None
    next_level_summary: str | None
    campaign_complete: bool
    level_best_score: int | None
    level_best_improved: bool
