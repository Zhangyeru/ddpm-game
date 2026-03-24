import type { ScoreHistoryEntry, SessionSnapshot } from "./types";

const SCORE_HISTORY_STORAGE_PREFIX = "noise-archaeologist-score-history";
const SCORE_HISTORY_LIMIT = 10;

function storageKey(playerId: string): string {
  return `${SCORE_HISTORY_STORAGE_PREFIX}:${playerId}`;
}

export function readScoreHistory(playerId: string): ScoreHistoryEntry[] {
  try {
    const raw = window.localStorage.getItem(storageKey(playerId));
    if (!raw) {
      return [];
    }

    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) {
      return [];
    }

    return parsed.slice(0, SCORE_HISTORY_LIMIT) as ScoreHistoryEntry[];
  } catch {
    return [];
  }
}

export function saveFinishedSessionHistory(
  playerId: string,
  session: SessionSnapshot
): ScoreHistoryEntry[] {
  if (session.status === "playing" || !session.ended_at) {
    return readScoreHistory(playerId);
  }

  const nextEntry: ScoreHistoryEntry = {
    player_id: playerId,
    session_id: session.session_id,
    ended_at: session.ended_at,
    status: session.status,
    revealed_target: session.revealed_target,
    mission_title: session.mission_title,
    final_score: session.score,
    score_breakdown: session.score_breakdown,
    score_events: session.score_events,
    loss_reason: session.loss_reason
  };
  const existing = readScoreHistory(playerId);
  const nextHistory = [
    nextEntry,
    ...existing.filter((entry) => entry.session_id !== session.session_id)
  ].slice(0, SCORE_HISTORY_LIMIT);

  try {
    window.localStorage.setItem(
      storageKey(playerId),
      JSON.stringify(nextHistory)
    );
  } catch {
    return nextHistory;
  }

  return nextHistory;
}
