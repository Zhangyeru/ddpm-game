import type {
  AuthResponse,
  AuthSessionSnapshot,
  CardId,
  FreezeRegionId,
  LeaderboardEntry,
  ProgressSnapshot,
  SessionSnapshot,
  TargetFamily
} from "../game/types";
import { readAuthToken } from "./authStorage";

const DEFAULT_API_BASE_URL = "http://localhost:8000/api";
const API_BASE_URL = normalizeBaseUrl(
  import.meta.env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL
);
const API_ORIGIN = resolveApiOrigin(API_BASE_URL);
const PLAYER_ID_STORAGE_KEY = "noise-archaeologist-player-id";
let inMemoryPlayerId: string | null = null;

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

function normalizeBaseUrl(value: string): string {
  const trimmed = value.trim();
  return trimmed.endsWith("/") ? trimmed.slice(0, -1) : trimmed;
}

function normalizePath(path: string): string {
  return path.startsWith("/") ? path : `/${path}`;
}

function isAbsoluteUrl(value: string): boolean {
  try {
    new URL(value);
    return true;
  } catch {
    return false;
  }
}

function resolveApiOrigin(baseUrl: string): string | null {
  if (isAbsoluteUrl(baseUrl)) {
    return new URL(baseUrl).origin;
  }

  return typeof window === "undefined" ? null : window.location.origin;
}

function resolveRequestUrl(path: string): string {
  const normalizedPath = normalizePath(path);

  if (isAbsoluteUrl(API_BASE_URL)) {
    return `${API_BASE_URL}${normalizedPath}`;
  }

  const normalizedBase = API_BASE_URL.startsWith("/")
    ? API_BASE_URL
    : `/${API_BASE_URL}`;
  return `${normalizedBase}${normalizedPath}`;
}

function generatePlayerId(): string {
  try {
    if (typeof window !== "undefined" && typeof window.crypto?.randomUUID === "function") {
      return window.crypto.randomUUID();
    }
  } catch {
    // Fall back to non-crypto ID generation below.
  }

  try {
    if (typeof window !== "undefined" && typeof window.crypto?.getRandomValues === "function") {
      const bytes = new Uint8Array(16);
      window.crypto.getRandomValues(bytes);
      return `anon-${Array.from(bytes, (value) => value.toString(16).padStart(2, "0")).join("")}`;
    }
  } catch {
    // Fall back to timestamp/random below.
  }

  return `anon-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`;
}

export function getPlayerId(): string {
  try {
    const existing = window.localStorage.getItem(PLAYER_ID_STORAGE_KEY);
    if (existing) {
      return existing;
    }
  } catch {
    // Continue with in-memory fallback.
  }

  if (inMemoryPlayerId) {
    return inMemoryPlayerId;
  }

  const next = generatePlayerId();
  inMemoryPlayerId = next;

  try {
    window.localStorage.setItem(PLAYER_ID_STORAGE_KEY, next);
  } catch {
    // Keep using the in-memory ID for this page session.
  }

  return next;
}

async function request<T>(
  path: string,
  init?: RequestInit
): Promise<T> {
  const headers = new Headers(init?.headers);
  const token = readAuthToken();
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  } else {
    headers.set("X-Player-Id", getPlayerId());
  }
  if (init?.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(resolveRequestUrl(path), {
    headers,
    ...init
  });

  if (!response.ok) {
    const contentType = response.headers.get("Content-Type") ?? "";
    if (contentType.includes("application/json")) {
      const payload = (await response.json()) as {
        detail?: string;
      };
      throw new ApiError(response.status, payload.detail || "接口请求失败。");
    }

    const message = await response.text();
    throw new ApiError(response.status, message || "接口请求失败。");
  }

  return (await response.json()) as T;
}

export function registerUser(
  username: string,
  password: string
): Promise<AuthResponse> {
  return request<AuthResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify({ username, password })
  });
}

export function loginUser(
  username: string,
  password: string
): Promise<AuthResponse> {
  return request<AuthResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password })
  });
}

export function getCurrentUser(): Promise<AuthSessionSnapshot> {
  return request<AuthSessionSnapshot>("/auth/me");
}

export function getLeaderboard(): Promise<LeaderboardEntry[]> {
  return request<LeaderboardEntry[]>("/leaderboard");
}

export function startSession(): Promise<SessionSnapshot> {
  return request<SessionSnapshot>("/session/start", {
    method: "POST"
  });
}

export function getProgression(): Promise<ProgressSnapshot> {
  return request<ProgressSnapshot>("/progression");
}

export function startCurrentLevel(): Promise<SessionSnapshot> {
  return request<SessionSnapshot>("/session/start-current-level", {
    method: "POST"
  });
}

export function startSpecificLevel(
  levelId: string
): Promise<SessionSnapshot> {
  return request<SessionSnapshot>(`/session/start-level/${levelId}`, {
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

export function commitFamily(
  sessionId: string,
  family: TargetFamily
): Promise<SessionSnapshot> {
  return request<SessionSnapshot>(`/session/${sessionId}/commit-family`, {
    method: "POST",
    body: JSON.stringify({ family })
  });
}

export function freezeRegion(
  sessionId: string,
  region: FreezeRegionId
): Promise<SessionSnapshot> {
  return request<SessionSnapshot>(`/session/${sessionId}/freeze`, {
    method: "POST",
    body: JSON.stringify({ region })
  });
}

export function advanceLevel(
  sessionId: string
): Promise<SessionSnapshot> {
  return request<SessionSnapshot>(`/session/${sessionId}/advance`, {
    method: "POST"
  });
}

export function resolveApiUrl(path: string): string {
  if (isAbsoluteUrl(path)) {
    return path;
  }

  const normalizedPath = normalizePath(path);
  if (API_ORIGIN === null) {
    return normalizedPath;
  }

  return new URL(normalizedPath, API_ORIGIN).toString();
}
