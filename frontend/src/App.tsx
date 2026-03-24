import { useEffect, useState } from "react";
import { GameCanvas } from "./components/GameCanvas";
import { GuessPanel } from "./components/GuessPanel";
import { HistoryDrawer } from "./components/HistoryDrawer";
import { InlineError } from "./components/InlineError";
import { LandingGuide } from "./components/LandingGuide";
import { LeaderboardPage } from "./components/LeaderboardPage";
import { LoadingRoundShell } from "./components/LoadingRoundShell";
import { RulePanel } from "./components/RulePanel";
import { ScorePanel } from "./components/ScorePanel";
import { StatusBar } from "./components/StatusBar";
import { ToolPanel } from "./components/ToolPanel";
import { useGameSession } from "./game/useGameSession";

type AppPage = "home" | "leaderboard";

function readAppPage(): AppPage {
  return window.location.hash === "#leaderboard" ? "leaderboard" : "home";
}

export default function App() {
  const [historyOpen, setHistoryOpen] = useState(false);
  const [page, setPage] = useState<AppPage>(() => readAppPage());
  const {
    authBusyAction,
    authError,
    authUser,
    controlsDisabled,
    error,
    leaderboard,
    leaderboardError,
    leaderboardLoading,
    pendingAction,
    progression,
    progressionLoading,
    guessReminder,
    selectedGuess,
    session,
    history,
    applyCard,
    applyFreeze,
    advanceToNextLevel,
    clearAuthError,
    startRound,
    login,
    logout,
    register,
    submitGuessChoice,
    submitFamilyCommit,
    retryLastAction,
    retryLeaderboard,
    clearError
  } = useGameSession({ autoStepEnabled: page !== "leaderboard" });

  useEffect(() => {
    function handleHashChange() {
      setPage(readAppPage());
    }

    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

  function openLeaderboard() {
    window.location.hash = "leaderboard";
  }

  function openHome() {
    if (window.location.hash) {
      window.history.replaceState(
        null,
        "",
        `${window.location.pathname}${window.location.search}`
      );
    }
    setPage("home");
  }

  return (
    <div className="app-shell">
      <StatusBar
        authBusyAction={authBusyAction}
        authUser={authUser}
        busyAction={pendingAction}
        historyCount={history.length}
        leaderboardOpen={page === "leaderboard"}
        onOpenLeaderboard={() => {
          if (page === "leaderboard") {
            openHome();
            return;
          }
          openLeaderboard();
        }}
        onOpenHistory={() => setHistoryOpen(true)}
        onLogout={() => {
          void logout();
        }}
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

      {page === "leaderboard" ? (
        <LeaderboardPage
          authUser={authUser}
          entries={leaderboard}
          error={leaderboardError}
          loading={leaderboardLoading}
          onBack={openHome}
          onRetry={() => {
            void retryLeaderboard();
          }}
          progression={progression}
        />
      ) : !session && (pendingAction === "start" || progressionLoading) ? (
        <LoadingRoundShell />
      ) : !session ? (
        <LandingGuide
          authBusyAction={authBusyAction}
          authError={authError}
          authUser={authUser}
          busy={pendingAction === "start"}
          onClearAuthError={clearAuthError}
          onLogin={login}
          onLogout={logout}
          onOpenLeaderboard={openLeaderboard}
          onRegister={register}
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
              guessReminder={guessReminder}
              labels={session.candidate_labels}
              missionTitle={session.mission_title}
              onGuess={(label) => {
                void submitGuessChoice(label);
              }}
              selectedGuess={selectedGuess}
            />
            <GameCanvas session={session} />
          </div>

          <div className="console-stack console-stack--right">
            <RulePanel
              busyAction={pendingAction}
              disabled={controlsDisabled}
              onCommitFamily={(family) => {
                void submitFamilyCommit(family);
              }}
              onFreeze={(region) => {
                void applyFreeze(region);
              }}
              session={session}
            />
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
