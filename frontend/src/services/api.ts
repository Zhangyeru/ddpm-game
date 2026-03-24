import type {
  CardId,
  SessionSnapshot
} from "../game/types";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";
const API_ORIGIN = new URL(API_BASE_URL).origin;
const PLAYER_ID_STORAGE_KEY = "noise-archaeologist-player-id";

export function getPlayerId(): string {
  try {
    const existing = window.localStorage.getItem(PLAYER_ID_STORAGE_KEY);
    if (existing) {
      return existing;
    }

    const next = window.crypto.randomUUID();
    window.localStorage.setItem(PLAYER_ID_STORAGE_KEY, next);
    return next;
  } catch {
    return "anonymous";
  }
}

async function request<T>(
  path: string,
  init?: RequestInit
): Promise<T> {
  const headers = new Headers(init?.headers);
  headers.set("X-Player-Id", getPlayerId());
  if (init?.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers,
    ...init
  });

  if (!response.ok) {
    const contentType = response.headers.get("Content-Type") ?? "";
    if (contentType.includes("application/json")) {
      const payload = (await response.json()) as {
        detail?: string;
      };
      throw new Error(payload.detail || "接口请求失败。");
    }

    const message = await response.text();
    throw new Error(message || "接口请求失败。");
  }

  return (await response.json()) as T;
}

export function startSession(): Promise<SessionSnapshot> {
  return request<SessionSnapshot>("/session/start", {
    method: "POST"
  });
}

export function stepSession(
  sessionId: string
): Promise<SessionSnapshot> {
  return request<SessionSnapshot>(`/session/${sessionId}/step`, {
    method: "POST"
  });
}

export function submitGuess(
  sessionId: string,
  label: string
): Promise<SessionSnapshot> {
  return request<SessionSnapshot>(`/session/${sessionId}/guess`, {
    method: "POST",
    body: JSON.stringify({ label })
  });
}

export function useCard(
  sessionId: string,
  cardId: CardId
): Promise<SessionSnapshot> {
  return request<SessionSnapshot>(`/session/${sessionId}/use-card`, {
    method: "POST",
    body: JSON.stringify({ card_id: cardId })
  });
}

export function resolveApiUrl(path: string): string {
  return new URL(path, API_ORIGIN).toString();
}
