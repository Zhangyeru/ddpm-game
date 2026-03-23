import type {
  CardId,
  FreezeRegion,
  SessionSnapshot
} from "../game/types";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api";

async function request<T>(
  path: string,
  init?: RequestInit
): Promise<T> {
  const headers = new Headers(init?.headers);
  if (init?.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers,
    ...init
  });

  if (!response.ok) {
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

export function freezeRegion(
  sessionId: string,
  region: FreezeRegion
): Promise<SessionSnapshot> {
  return request<SessionSnapshot>(`/session/${sessionId}/freeze`, {
    method: "POST",
    body: JSON.stringify({ region })
  });
}
