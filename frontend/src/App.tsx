import { useState } from "react";
import { GameCanvas } from "./components/GameCanvas";
import { GuessPanel } from "./components/GuessPanel";
import { HistoryDrawer } from "./components/HistoryDrawer";
import { InlineError } from "./components/InlineError";
import { LandingGuide } from "./components/LandingGuide";
import { LoadingRoundShell } from "./components/LoadingRoundShell";
import { ScorePanel } from "./components/ScorePanel";
import { StatusBar } from "./components/StatusBar";
import { ToolPanel } from "./components/ToolPanel";
import { useGameSession } from "./game/useGameSession";

export default function App() {
  const [historyOpen, setHistoryOpen] = useState(false);
  const {
    controlsDisabled,
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
    clearError
  } = useGameSession();

  return (
    <div className="app-shell">
      <StatusBar
        busyAction={pendingAction}
        historyCount={history.length}
        onOpenHistory={() => setHistoryOpen(true)}
        onStart={() => {
          void startRound();
        }}
        progression={progression}
        session={session}
      />

      {error ? (
        <InlineError
          detail={`${error.detail} 你可以重试刚才的操作，或重新开始本局。`}
          onDismiss={clearError}
          onRetry={() => {
            void retryLastAction();
          }}
          title={error.title}
        />
      ) : null}

      {!session && (pendingAction === "start" || progressionLoading) ? (
        <LoadingRoundShell />
      ) : !session ? (
        <LandingGuide
          busy={pendingAction === "start"}
          progression={progression}
          onStart={() => {
            void startRound();
          }}
        />
      ) : (
        <main className="console-grid">
          <div className="console-stack console-stack--left">
            <ScorePanel
              busyAction={pendingAction}
              historyCount={history.length}
              onAdvance={() => {
                void advanceToNextLevel();
              }}
              onOpenHistory={() => setHistoryOpen(true)}
              onRetryLevel={() => {
                void startRound();
              }}
              progression={progression}
              session={session}
            />
          </div>

          <div className="console-stack console-stack--center">
            <GuessPanel
              busyAction={pendingAction}
              disabled={controlsDisabled}
              labels={session.candidate_labels}
              missionTitle={session.mission_title}
              onConfirm={() => {
                void submitSelectedGuess();
              }}
              onSelect={setSelectedGuess}
              selectedGuess={selectedGuess}
            />
            <GameCanvas session={session} />
          </div>

          <div className="console-stack console-stack--right">
            <ToolPanel
              busyAction={pendingAction}
              disabled={controlsDisabled}
              onUseCard={(cardId) => {
                void applyCard(cardId);
              }}
              session={session}
            />
          </div>
        </main>
      )}

      <HistoryDrawer
        history={history}
        onClose={() => setHistoryOpen(false)}
        open={historyOpen}
      />
    </div>
  );
}
