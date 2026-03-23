export type CardId =
  | "sharpen-outline"
  | "mechanical-lens"
  | "bio-scan";

export type FreezeRegion = "upper-left" | "center" | "lower-right";

export type GameStatus = "playing" | "won" | "lost";

export interface CardOption {
  id: CardId;
  title: string;
  summary: string;
}

export interface FreezeRegionOption {
  id: FreezeRegion;
  title: string;
  summary: string;
}

export interface SessionSnapshot {
  session_id: string;
  chapter: number;
  level: number;
  score: number;
  combo: number;
  status: GameStatus;
  frames_remaining: number;
  seconds_remaining: number;
  stability: number;
  corruption: number;
  scan_charges: number;
  frame_index: number;
  total_frames: number;
  progress: number;
  image_url: string;
  candidate_labels: string[];
  remaining_guesses: number;
  cards_remaining: number;
  freeze_available: boolean;
  hint: string;
  events: string[];
  card_options: CardOption[];
  freeze_region_options: FreezeRegionOption[];
  used_cards: CardId[];
  frozen_region: FreezeRegion | null;
  revealed_target: string | null;
  signature_clue: string | null;
  signature_revealed: boolean;
  phase_label: string;
  mission_title: string;
  threat_label: string;
  step_interval_ms: number;
}
