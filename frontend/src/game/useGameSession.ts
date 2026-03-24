import { useEffect, useRef, useState } from "react";
import type {
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
  getPlayerId,
  getProgression,
  startCurrentLevel,
  stepSession,
  submitGuess,
  useCard
} from "../services/api";

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

export function useGameSession() {
  const playerIdRef = useRef(getPlayerId());
  const [session, setSession] = useState<SessionSnapshot | null>(null);
  const [progression, setProgression] = useState<ProgressSnapshot | null>(null);
  const [progressionLoading, setProgressionLoading] = useState(true);
  const [history, setHistory] = useState<ScoreHistoryEntry[]>(() =>
    readScoreHistory(playerIdRef.current)
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
    void loadProgression();

    return () => {
      mountedRef.current = false;
      requestSequenceRef.current += 1;
      progressionSequenceRef.current += 1;
    };
  }, []);

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

    setHistory(saveFinishedSessionHistory(playerIdRef.current, session));
  }, [session]);

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

  return {
    controlsDisabled:
      pendingAction !== null || !session || session.status !== "playing",
    error,
    pendingAction,
    progression,
    progressionLoading,
    selectedGuess,
    session,
    history,
    setSelectedGuess,
    applyCard,
    advanceToNextLevel,
    startRound,
    submitSelectedGuess,
    retryLastAction,
    clearError: () => setError(null)
  };
}
