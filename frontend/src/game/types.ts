export type CardId =
  | "sharpen-outline"
  | "mechanical-lens"
  | "bio-scan";

export type GameStatus = "playing" | "won" | "lost";
export type PendingActionKind =
  | "advance"
  | "login"
  | "progression"
  | "logout"
  | "register"
  | "start"
  | "step"
  | "guess"
  | "card";
export type ScoreEventKind =
  | "card"
  | "guess_penalty"
  | "settlement"
  | "loss";

export interface CardOption {
  id: CardId;
  title: string;
  summary: string;
}

export interface ScoreBreakdown {
  process_score_total: number;
  base_score: number;
  early_bonus: number;
  time_bonus: number;
  stability_bonus: number;
  low_corruption_bonus: number;
  mission_bonus: number;
  card_penalty: number;
  settlement_score: number;
  final_score: number;
}

export interface ScoreEvent {
  kind: ScoreEventKind;
  title: string;
  delta: number;
  running_score: number;
  detail: string;
}

export interface LevelProgressItem {
  level_id: string;
  chapter: number;
  level: number;
  chapter_title: string;
  level_title: string;
  mission_title: string;
  summary: string;
  max_guesses: number;
  max_cards: number;
  candidate_count: number;
  is_current: boolean;
  is_completed: boolean;
  is_unlocked: boolean;
}

export interface ProgressSnapshot {
  current_level_id: string;
  highest_unlocked_level_id: string;
  completed_level_ids: string[];
  completed_count: number;
  total_levels: number;
  campaign_complete: boolean;
  current_level: LevelProgressItem;
  levels: LevelProgressItem[];
}

export interface AuthUser {
  id: string;
  username: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: "bearer";
  user: AuthUser;
  progression: ProgressSnapshot;
}

export interface AuthSessionSnapshot {
  user: AuthUser;
  progression: ProgressSnapshot;
}

export interface SessionSnapshot {
  session_id: string;
  level_id: string;
  chapter: number;
  level: number;
  chapter_title: string;
  level_title: string;
  level_summary: string;
  score: number;
  combo: number;
  status: GameStatus;
  frames_remaining: number;
  seconds_remaining: number;
  stability: number;
  corruption: number;
  frame_index: number;
  total_frames: number;
  progress: number;
  image_url: string;
  candidate_labels: string[];
  remaining_guesses: number;
  max_guesses: number;
  cards_remaining: number;
  max_cards: number;
  hint: string;
  events: string[];
  card_options: CardOption[];
  used_cards: CardId[];
  revealed_target: string | null;
  phase_label: string;
  mission_title: string;
  threat_label: string;
  step_interval_ms: number;
  score_breakdown: ScoreBreakdown | null;
  score_events: ScoreEvent[];
  loss_reason: string | null;
  ended_at: string | null;
  awaiting_advancement: boolean;
  next_level_id: string | null;
  next_level_title: string | null;
  next_level_summary: string | null;
  campaign_complete: boolean;
}

export interface ScoreHistoryEntry {
  player_id: string;
  session_id: string;
  ended_at: string;
  status: Exclude<GameStatus, "playing">;
  level_id: string;
  chapter: number;
  level: number;
  chapter_title: string;
  level_title: string;
  revealed_target: string | null;
  mission_title: string;
  final_score: number;
  score_breakdown: ScoreBreakdown | null;
  score_events: ScoreEvent[];
  loss_reason: string | null;
}
