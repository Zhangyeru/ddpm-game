import { lazy, Suspense, useCallback, useEffect, useState } from "react";
import { GameCanvas } from "./components/GameCanvas";
import { GuessPanel } from "./components/GuessPanel";
import { InlineError } from "./components/InlineError";
import { LoadingRoundShell } from "./components/LoadingRoundShell";
import { RulePanel } from "./components/RulePanel";
import { ScorePanel } from "./components/ScorePanel";
import { StatusBar } from "./components/StatusBar";
import { ToolPanel } from "./components/ToolPanel";
import { useGameSession } from "./game/useGameSession";

const HistoryDrawer = lazy(() => import("./components/HistoryDrawer").then((m) => ({ default: m.HistoryDrawer })));
const LandingGuide = lazy(() => import("./components/LandingGuide").then((m) => ({ default: m.LandingGuide })));
const LeaderboardPage = lazy(() => import("./components/LeaderboardPage").then((m) => ({ default: m.LeaderboardPage })));
const LevelTransitionCard = lazy(() => import("./components/LevelTransitionCard").then((m) => ({ default: m.LevelTransitionCard })));

type AppPage = "home" | "leaderboard";

function readAppPage(): AppPage {
  return window.location.hash === "#leaderboard" ? "leaderboard" : "home";
}

export default function App() {
  const [historyOpen, setHistoryOpen] = useState(false);
  const [page, setPage] = useState<AppPage>(() => readAppPage());
  const [showTransition, setShowTransition] = useState(false);
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
    startSelectedLevel,
    exitSession,
    clearError
  } = useGameSession({ autoStepEnabled: page !== "leaderboard" && !showTransition });

  useEffect(() => {
    function handleHashChange() {
      setPage(readAppPage());
    }

    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

  useEffect(() => {
    if (session && progression?.current_level) {
      setShowTransition(true);
    }
  }, [session?.session_id]);

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

  function returnHomeFromSession() {
    setShowTransition(false);
    exitSession();
    openHome();
  }

  const closeTransition = useCallback(() => {
    setShowTransition(false);
  }, []);

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
        onOpenHome={returnHomeFromSession}
        onStart={() => {
          void startRound();
        }}
        progression={progression}
        session={session}
      />

      {showTransition && session ? (
        <Suspense fallback={null}>
          <LevelTransitionCard
            session={session}
            onTransitionComplete={closeTransition}
          />
        </Suspense>
      ) : null}

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
        <Suspense fallback={<LoadingRoundShell />}>
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
        </Suspense>
      ) : !session && (pendingAction === "start" || progressionLoading) ? (
        <LoadingRoundShell />
      ) : !session ? (
        <Suspense fallback={<LoadingRoundShell />}>
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
            onStartLevel={(levelId) => {
              void startSelectedLevel(levelId);
            }}
          />
        </Suspense>
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

      {historyOpen ? (
        <Suspense fallback={null}>
          <HistoryDrawer
            history={history}
            onClose={() => setHistoryOpen(false)}
            open={historyOpen}
          />
        </Suspense>
      ) : null}
    </div>
  );
}
