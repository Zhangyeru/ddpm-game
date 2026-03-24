import { useEffect, useRef, useState } from "react";
import type {
  AuthUser,
  CardId,
  PendingActionKind,
  ProgressSnapshot,
  ScoreHistoryEntry,
  SessionSnapshot
} from "./types";
import {
  readScoreHistory,
  saveFinishedSessionHistory
} from "./scoreHistory";
import {
  advanceLevel,
  getCurrentUser,
  getPlayerId,
  getProgression,
  loginUser,
  registerUser,
  startCurrentLevel,
  stepSession,
  submitGuess,
  useCard
} from "../services/api";
import {
  clearAuthSession,
  readAuthToken,
  readAuthUser,
  saveAuthSession
} from "../services/authStorage";

type SessionRequestOptions = {
  keepGuess?: boolean;
};

type SessionErrorState = {
  detail: string;
  title: string;
};

type SessionRequestDescriptor = {
  kind: PendingActionKind;
  requestFactory: () => Promise<SessionSnapshot>;
  title: string;
  options?: SessionRequestOptions;
};

function getErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }

  return "请求失败，请稍后重试。";
}

function historyOwnerKey(user: AuthUser | null, anonymousPlayerId: string): string {
  if (user) {
    return `user:${user.id}`;
  }

  return `anon:${anonymousPlayerId}`;
}

export function useGameSession() {
  const playerIdRef = useRef(getPlayerId());
  const authRequestSequenceRef = useRef(0);
  const initialAuthUser = readAuthUser();
  const initialHistoryOwner = historyOwnerKey(initialAuthUser, playerIdRef.current);
  const [session, setSession] = useState<SessionSnapshot | null>(null);
  const [progression, setProgression] = useState<ProgressSnapshot | null>(null);
  const [progressionLoading, setProgressionLoading] = useState(true);
  const [authUser, setAuthUser] = useState<AuthUser | null>(initialAuthUser);
  const [authPendingAction, setAuthPendingAction] = useState<
    Extract<PendingActionKind, "login" | "logout" | "register"> | null
  >(null);
  const [authError, setAuthError] = useState<string | null>(null);
  const [historyOwner, setHistoryOwner] = useState(initialHistoryOwner);
  const [history, setHistory] = useState<ScoreHistoryEntry[]>(() =>
    readScoreHistory(initialHistoryOwner)
  );
  const [selectedGuess, setSelectedGuess] = useState<string | null>(null);
  const [pendingAction, setPendingAction] = useState<PendingActionKind | null>(null);
  const [error, setError] = useState<SessionErrorState | null>(null);
  const mountedRef = useRef(true);
  const requestSequenceRef = useRef(0);
  const progressionSequenceRef = useRef(0);
  const lastFailedRequestRef = useRef<SessionRequestDescriptor | null>(null);

  useEffect(() => {
    mountedRef.current = true;
    void bootstrapSessionState();

    return () => {
      mountedRef.current = false;
      requestSequenceRef.current += 1;
      progressionSequenceRef.current += 1;
      authRequestSequenceRef.current += 1;
    };
  }, []);

  async function bootstrapSessionState() {
    const requestId = progressionSequenceRef.current + 1;
    progressionSequenceRef.current = requestId;
    setProgressionLoading(true);

    const token = readAuthToken();
    if (token) {
      try {
        const authSession = await getCurrentUser();
        if (!mountedRef.current || requestId !== progressionSequenceRef.current) {
          return;
        }

        setAuthUser(authSession.user);
        setAuthError(null);
        setProgression(authSession.progression);
        const nextHistoryOwner = historyOwnerKey(authSession.user, playerIdRef.current);
        setHistoryOwner(nextHistoryOwner);
        setHistory(readScoreHistory(nextHistoryOwner));
        setProgressionLoading(false);
        return;
      } catch {
        clearAuthSession();
        if (!mountedRef.current || requestId !== progressionSequenceRef.current) {
          return;
        }
        setAuthUser(null);
      }
    }

    try {
      const next = await getProgression();
      if (!mountedRef.current || requestId !== progressionSequenceRef.current) {
        return;
      }
      const nextHistoryOwner = historyOwnerKey(null, playerIdRef.current);
      setHistoryOwner(nextHistoryOwner);
      setHistory(readScoreHistory(nextHistoryOwner));
      setProgression(next);
    } catch {
      if (!mountedRef.current || requestId !== progressionSequenceRef.current) {
        return;
      }
    } finally {
      if (mountedRef.current && requestId === progressionSequenceRef.current) {
        setProgressionLoading(false);
      }
    }
  }

  async function loadProgression(silent = false) {
    const requestId = progressionSequenceRef.current + 1;
    progressionSequenceRef.current = requestId;
    if (!silent || progression === null) {
      setProgressionLoading(true);
    }

    try {
      const next = await getProgression();
      if (!mountedRef.current || requestId !== progressionSequenceRef.current) {
        return;
      }
      setProgression(next);
    } catch {
      if (!mountedRef.current || requestId !== progressionSequenceRef.current) {
        return;
      }
    } finally {
      if (
        mountedRef.current &&
        requestId === progressionSequenceRef.current &&
        (!silent || progression === null)
      ) {
        setProgressionLoading(false);
      }
    }
  }

  async function runSessionRequest(descriptor: SessionRequestDescriptor) {
    const requestId = requestSequenceRef.current + 1;
    requestSequenceRef.current = requestId;
    setPendingAction(descriptor.kind);
    setError(null);

    try {
      const next = await descriptor.requestFactory();
      if (!mountedRef.current || requestId !== requestSequenceRef.current) {
        return;
      }

      lastFailedRequestRef.current = null;
      setSession(next);
      setSelectedGuess((current) => {
        if (
          descriptor.options?.keepGuess &&
          current &&
          next.candidate_labels.includes(current)
        ) {
          return current;
        }

        if (
          next.status === "playing" &&
          current &&
          next.candidate_labels.includes(current)
        ) {
          return current;
        }

        return null;
      });
    } catch (requestError) {
      if (!mountedRef.current || requestId !== requestSequenceRef.current) {
        return;
      }

      lastFailedRequestRef.current = descriptor;
      setError({
        detail: getErrorMessage(requestError),
        title: `${descriptor.title}未完成`
      });
    } finally {
      if (mountedRef.current && requestId === requestSequenceRef.current) {
        setPendingAction(null);
      }
    }
  }

  useEffect(() => {
    if (!session || session.status !== "playing" || pendingAction) {
      return;
    }

    const timer = window.setTimeout(() => {
      void runSessionRequest({
        kind: "step",
        options: {
          keepGuess: true
        },
        requestFactory: () => stepSession(session.session_id),
        title: "自动解码"
      });
    }, session.step_interval_ms);

    return () => window.clearTimeout(timer);
  }, [pendingAction, session]);

  useEffect(() => {
    if (!session) {
      return;
    }

    void loadProgression(true);
  }, [session?.session_id, session?.status]);

  useEffect(() => {
    if (!session || session.status === "playing" || !session.ended_at) {
      return;
    }

    setHistory(saveFinishedSessionHistory(historyOwner, session));
  }, [historyOwner, session]);

  async function runAuthRequest(
    kind: Extract<PendingActionKind, "login" | "register">,
    requestFactory: () => Promise<{
      access_token: string;
      progression: ProgressSnapshot;
      user: AuthUser;
    }>
  ) {
    const requestId = authRequestSequenceRef.current + 1;
    authRequestSequenceRef.current = requestId;
    setAuthPendingAction(kind);
    setAuthError(null);

    try {
      const response = await requestFactory();
      if (!mountedRef.current || requestId !== authRequestSequenceRef.current) {
        return false;
      }

      saveAuthSession(response.access_token, response.user);
      setAuthUser(response.user);
      setProgression(response.progression);
      setSession(null);
      setSelectedGuess(null);
      setError(null);
      lastFailedRequestRef.current = null;
      const nextHistoryOwner = historyOwnerKey(response.user, playerIdRef.current);
      setHistoryOwner(nextHistoryOwner);
      setHistory(readScoreHistory(nextHistoryOwner));
      return true;
    } catch (requestError) {
      if (!mountedRef.current || requestId !== authRequestSequenceRef.current) {
        return false;
      }

      setAuthError(getErrorMessage(requestError));
      return false;
    } finally {
      if (mountedRef.current && requestId === authRequestSequenceRef.current) {
        setAuthPendingAction(null);
      }
    }
  }

  async function startRound() {
    setSelectedGuess(null);
    await runSessionRequest({
      kind: "start",
      requestFactory: () => startCurrentLevel(),
      title: progression?.completed_count ? "开始当前关" : "开始第一关"
    });
  }

  async function advanceToNextLevel() {
    if (!session) {
      return;
    }

    setSelectedGuess(null);
    await runSessionRequest({
      kind: "advance",
      requestFactory: () => advanceLevel(session.session_id),
      title: "进入下一关"
    });
  }

  async function submitSelectedGuess() {
    if (!session || !selectedGuess) {
      return;
    }

    await runSessionRequest({
      kind: "guess",
      requestFactory: () => submitGuess(session.session_id, selectedGuess),
      title: "提交猜测"
    });
  }

  async function applyCard(cardId: CardId) {
    if (!session) {
      return;
    }

    await runSessionRequest({
      kind: "card",
      options: {
        keepGuess: true
      },
      requestFactory: () => useCard(session.session_id, cardId),
      title: "应用引导卡"
    });
  }

  async function retryLastAction() {
    if (!lastFailedRequestRef.current) {
      return;
    }

    await runSessionRequest(lastFailedRequestRef.current);
  }

  async function login(username: string, password: string) {
    await runAuthRequest("login", () => loginUser(username, password));
  }

  async function register(username: string, password: string) {
    await runAuthRequest("register", () => registerUser(username, password));
  }

  async function logout() {
    const requestId = authRequestSequenceRef.current + 1;
    authRequestSequenceRef.current = requestId;
    setAuthPendingAction("logout");
    setAuthError(null);
    clearAuthSession();
    setAuthUser(null);
    setSession(null);
    setSelectedGuess(null);
    setError(null);
    lastFailedRequestRef.current = null;

    const nextHistoryOwner = historyOwnerKey(null, playerIdRef.current);
    setHistoryOwner(nextHistoryOwner);
    setHistory(readScoreHistory(nextHistoryOwner));

    try {
      const next = await getProgression();
      if (!mountedRef.current || requestId !== authRequestSequenceRef.current) {
        return;
      }
      setProgression(next);
    } catch (requestError) {
      if (!mountedRef.current || requestId !== authRequestSequenceRef.current) {
        return;
      }
      setAuthError(getErrorMessage(requestError));
    } finally {
      if (mountedRef.current && requestId === authRequestSequenceRef.current) {
        setAuthPendingAction(null);
      }
    }
  }

  return {
    controlsDisabled:
      pendingAction !== null ||
      authPendingAction !== null ||
      !session ||
      session.status !== "playing",
    authBusyAction: authPendingAction,
    authError,
    authUser,
    error,
    pendingAction: authPendingAction ?? pendingAction,
    progression,
    progressionLoading,
    selectedGuess,
    session,
    history,
    setSelectedGuess,
    applyCard,
    advanceToNextLevel,
    login,
    logout,
    register,
    startRound,
    submitSelectedGuess,
    retryLastAction,
    clearAuthError: () => setAuthError(null),
    clearError: () => setError(null)
  };
}
