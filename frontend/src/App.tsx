import { useEffect, useState } from "react";
import { EventLog } from "./components/EventLog";
import { GameCanvas } from "./components/GameCanvas";
import { GuessPanel } from "./components/GuessPanel";
import { StatusBar } from "./components/StatusBar";
import { ToolPanel } from "./components/ToolPanel";
import type {
  CardId,
  FreezeRegion,
  SessionSnapshot
} from "./game/types";
import {
  freezeRegion,
  startSession,
  stepSession,
  submitGuess,
  useCard
} from "./services/api";

function getErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message;
  }

  return "请求失败，请稍后重试。";
}

export default function App() {
  const [session, setSession] = useState<SessionSnapshot | null>(null);
  const [selectedGuess, setSelectedGuess] = useState<string | null>(null);
  const [pendingAction, setPendingAction] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function syncSession(
    request: Promise<SessionSnapshot>,
    options?: { keepGuess?: boolean }
  ) {
    setPendingAction(true);
    setError(null);

    try {
      const next = await request;
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
      setError(getErrorMessage(requestError));
    } finally {
      setPendingAction(false);
    }
  }

  useEffect(() => {
    if (!session || session.status !== "playing" || pendingAction) {
      return;
    }

    const timer = window.setTimeout(() => {
      void syncSession(stepSession(session.session_id), {
        keepGuess: true
      });
    }, session.step_interval_ms);

    return () => window.clearTimeout(timer);
  }, [pendingAction, session]);

  async function handleStart() {
    setSelectedGuess(null);
    await syncSession(startSession());
  }

  async function handleGuess() {
    if (!session || !selectedGuess) {
      return;
    }

    await syncSession(submitGuess(session.session_id, selectedGuess));
  }

  async function handleUseCard(cardId: CardId) {
    if (!session) {
      return;
    }

    await syncSession(useCard(session.session_id, cardId), {
      keepGuess: true
    });
  }

  async function handleFreeze(region: FreezeRegion) {
    if (!session) {
      return;
    }

    await syncSession(freezeRegion(session.session_id, region), {
      keepGuess: true
    });
  }

  const controlsDisabled =
    pendingAction || !session || session.status !== "playing";

  return (
    <div className="app-shell">
      <StatusBar
        busy={pendingAction}
        onStart={() => {
          void handleStart();
        }}
        session={session}
      />

      {error ? <div className="error-banner">{error}</div> : null}

      {!session ? (
        <section className="panel intro-panel">
          <p className="eyebrow">原型目标</p>
          <h2>先验证玩法，再接入真实 DDPM 推理</h2>
          <p>
            当前版本使用程序生成的 SVG 帧来模拟去噪过程，重点先验证
            节奏、可读性、道具时机和计分反馈，再投入真实模型接入。
          </p>
          <button
            className="action-button"
            onClick={() => {
              void handleStart();
            }}
            type="button"
          >
            开始首局扫描
          </button>
        </section>
      ) : (
        <>
          <main className="layout-grid">
            <EventLog events={session.events} />
            <GameCanvas session={session} />
            <ToolPanel
              disabled={controlsDisabled}
              onFreeze={(region) => {
                void handleFreeze(region);
              }}
              onUseCard={(cardId) => {
                void handleUseCard(cardId);
              }}
              session={session}
            />
          </main>

          <GuessPanel
            disabled={controlsDisabled}
            labels={session.candidate_labels}
            onConfirm={() => {
              void handleGuess();
            }}
            onSelect={setSelectedGuess}
            selectedGuess={selectedGuess}
          />

          <section className="panel result-panel">
            <div>
              <p className="eyebrow">本局状态</p>
              <h2>
                {session.status === "playing"
                  ? "遗物仍在解码中"
                  : session.status === "won"
                    ? `识别成功：${session.revealed_target}`
                    : `识别失败：${session.revealed_target}`}
              </h2>
            </div>
            <p>
              连胜：<strong>{session.combo}</strong>
            </p>
          </section>
        </>
      )}
    </div>
  );
}
