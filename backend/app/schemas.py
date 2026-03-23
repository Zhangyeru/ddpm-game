from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


CardId = Literal["sharpen-outline", "mechanical-lens", "bio-scan"]
FreezeRegion = Literal["upper-left", "center", "lower-right"]
GameStatus = Literal["playing", "won", "lost"]


class GuessRequest(BaseModel):
    label: str


class UseCardRequest(BaseModel):
    card_id: CardId


class FreezeRequest(BaseModel):
    region: FreezeRegion


class SessionSnapshot(BaseModel):
    session_id: str
    chapter: int
    level: int
    score: int
    combo: int
    status: GameStatus
    time_remaining: int
    frame_index: int
    total_frames: int
    progress: float
    image_data: str
    candidate_labels: list[str]
    remaining_guesses: int
    cards_remaining: int
    freeze_available: bool
    hint: str
    events: list[str]
    used_cards: list[CardId]
    frozen_region: FreezeRegion | None
    revealed_target: str | None
    step_interval_ms: int

