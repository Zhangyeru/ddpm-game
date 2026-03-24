import { useEffect, useRef, useState } from "react";
import type {
  CardId,
  PendingActionKind,
  ScoreHistoryEntry,
  SessionSnapshot
} from "./types";
import {
  readScoreHistory,
  saveFinishedSessionHistory
} from "./scoreHistory";
import {
  getPlayerId,
  startSession,
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
  const [history, setHistory] = useState<ScoreHistoryEntry[]>(() =>
    readScoreHistory(playerIdRef.current)
  );
  const [selectedGuess, setSelectedGuess] = useState<string | null>(null);
  const [pendingAction, setPendingAction] = useState<PendingActionKind | null>(null);
  const [error, setError] = useState<SessionErrorState | null>(null);
  const mountedRef = useRef(true);
  const requestSequenceRef = useRef(0);
  const lastFailedRequestRef = useRef<SessionRequestDescriptor | null>(null);

  useEffect(() => {
    mountedRef.current = true;

    return () => {
      mountedRef.current = false;
      requestSequenceRef.current += 1;
    };
  }, []);

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
    if (!session || session.status === "playing" || !session.ended_at) {
      return;
    }

    setHistory(saveFinishedSessionHistory(playerIdRef.current, session));
  }, [session]);

  async function startRound() {
    setSelectedGuess(null);
    await runSessionRequest({
      kind: "start",
      requestFactory: () => startSession(),
      title: "启动扫描"
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
    selectedGuess,
    session,
    history,
    setSelectedGuess,
    applyCard,
    startRound,
    submitSelectedGuess,
    retryLastAction,
    clearError: () => setError(null)
  };
}
