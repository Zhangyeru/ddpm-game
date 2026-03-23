export type CardId =
  | "sharpen-outline"
  | "mechanical-lens"
  | "bio-scan";

export type FreezeRegion = "upper-left" | "center" | "lower-right";

export type GameStatus = "playing" | "won" | "lost";

export interface SessionSnapshot {
  session_id: string;
  chapter: number;
  level: number;
  score: number;
  combo: number;
  status: GameStatus;
  time_remaining: number;
  frame_index: number;
  total_frames: number;
  progress: number;
  image_data: string;
  candidate_labels: string[];
  remaining_guesses: number;
  cards_remaining: number;
  freeze_available: boolean;
  hint: string;
  events: string[];
  used_cards: CardId[];
  frozen_region: FreezeRegion | null;
  revealed_target: string | null;
  step_interval_ms: number;
}

