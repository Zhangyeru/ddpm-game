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


class CardOption(BaseModel):
    id: CardId
    title: str
    summary: str


class FreezeRegionOption(BaseModel):
    id: FreezeRegion
    title: str
    summary: str


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
    scan_charges: int
    frame_index: int
    total_frames: int
    progress: float
    image_url: str
    candidate_labels: list[str]
    remaining_guesses: int
    cards_remaining: int
    freeze_available: bool
    hint: str
    events: list[str]
    card_options: list[CardOption]
    freeze_region_options: list[FreezeRegionOption]
    used_cards: list[CardId]
    frozen_region: FreezeRegion | None
    revealed_target: str | None
    signature_clue: str | None
    signature_revealed: bool
    phase_label: str
    mission_title: str
    threat_label: str
    step_interval_ms: int
