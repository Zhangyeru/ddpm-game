import type { AuthUser } from "../game/types";

const AUTH_TOKEN_STORAGE_KEY = "noise-archaeologist-auth-token";
const AUTH_USER_STORAGE_KEY = "noise-archaeologist-auth-user";

export function readAuthToken(): string | null {
  try {
    return window.localStorage.getItem(AUTH_TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function readAuthUser(): AuthUser | null {
  try {
    const raw = window.localStorage.getItem(AUTH_USER_STORAGE_KEY);
    if (!raw) {
      return null;
    }

    const parsed = JSON.parse(raw) as Partial<AuthUser>;
    if (typeof parsed.id !== "string" || typeof parsed.username !== "string") {
      return null;
    }

    return {
      id: parsed.id,
      username: parsed.username
    };
  } catch {
    return null;
  }
}

export function saveAuthSession(token: string, user: AuthUser) {
  try {
    window.localStorage.setItem(AUTH_TOKEN_STORAGE_KEY, token);
    window.localStorage.setItem(AUTH_USER_STORAGE_KEY, JSON.stringify(user));
  } catch {
    // Ignore storage failures and keep the in-memory session.
  }
}

export function clearAuthSession() {
  try {
    window.localStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
    window.localStorage.removeItem(AUTH_USER_STORAGE_KEY);
  } catch {
    // Ignore storage failures when logging out.
  }
}
