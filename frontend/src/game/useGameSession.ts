import { useEffect, useRef, useState } from "react";
import type { CardId, FreezeRegion, SessionSnapshot } from "./types";
import {
  freezeRegion,
  pulseScan,
  startSession,
  stepSession,
  submitGuess,
  useCard
} from "../services/api";

type SessionRequestOptions = {
  keepGuess?: boolean;
};

function getErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }

  return "请求失败，请稍后重试。";
}

export function useGameSession() {
  const [session, setSession] = useState<SessionSnapshot | null>(null);
  const [selectedGuess, setSelectedGuess] = useState<string | null>(null);
  const [pendingAction, setPendingAction] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const mountedRef = useRef(true);
  const requestSequenceRef = useRef(0);

  useEffect(() => {
    mountedRef.current = true;

    return () => {
      mountedRef.current = false;
      requestSequenceRef.current += 1;
    };
  }, []);

  async function runSessionRequest(
    requestFactory: () => Promise<SessionSnapshot>,
    options?: SessionRequestOptions
  ) {
    const requestId = requestSequenceRef.current + 1;
    requestSequenceRef.current = requestId;
    setPendingAction(true);
    setError(null);

    try {
      const next = await requestFactory();
      if (!mountedRef.current || requestId !== requestSequenceRef.current) {
        return;
      }

      setSession(next);
      setSelectedGuess((current) => {
        if (
          options?.keepGuess &&
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

      setError(getErrorMessage(requestError));
    } finally {
      if (mountedRef.current && requestId === requestSequenceRef.current) {
        setPendingAction(false);
      }
    }
  }

  useEffect(() => {
    if (!session || session.status !== "playing" || pendingAction) {
      return;
    }

    const timer = window.setTimeout(() => {
      void runSessionRequest(() => stepSession(session.session_id), {
        keepGuess: true
      });
    }, session.step_interval_ms);

    return () => window.clearTimeout(timer);
  }, [pendingAction, session]);

  async function startRound() {
    setSelectedGuess(null);
    await runSessionRequest(() => startSession());
  }

  async function submitSelectedGuess() {
    if (!session || !selectedGuess) {
      return;
    }

    await runSessionRequest(() =>
      submitGuess(session.session_id, selectedGuess)
    );
  }

  async function applyCard(cardId: CardId) {
    if (!session) {
      return;
    }

    await runSessionRequest(() => useCard(session.session_id, cardId), {
      keepGuess: true
    });
  }

  async function applyFreeze(region: FreezeRegion) {
    if (!session) {
      return;
    }

    await runSessionRequest(
      () => freezeRegion(session.session_id, region),
      {
        keepGuess: true
      }
    );
  }

  async function runPulseScan() {
    if (!session) {
      return;
    }

    await runSessionRequest(() => pulseScan(session.session_id), {
      keepGuess: true
    });
  }

  return {
    controlsDisabled:
      pendingAction || !session || session.status !== "playing",
    error,
    pendingAction,
    selectedGuess,
    session,
    setSelectedGuess,
    applyCard,
    applyFreeze,
    runPulseScan,
    startRound,
    submitSelectedGuess
  };
}
