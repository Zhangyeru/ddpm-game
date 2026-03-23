import { EventLog } from "./components/EventLog";
import { GameCanvas } from "./components/GameCanvas";
import { GuessPanel } from "./components/GuessPanel";
import { StatusBar } from "./components/StatusBar";
import { ToolPanel } from "./components/ToolPanel";
import { useGameSession } from "./game/useGameSession";

export default function App() {
  const {
    controlsDisabled,
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
  } = useGameSession();

  return (
    <div className="app-shell">
      <StatusBar
        busy={pendingAction}
        onStart={() => {
          void startRound();
        }}
        session={session}
      />

      {error ? <div className="error-banner">{error}</div> : null}

      {!session ? (
        <section className="panel intro-panel">
          <p className="eyebrow">原型目标</p>
          <h2>高风险去噪判断，而不只是看图猜答案</h2>
          <p>
            当前版本已经加入稳定度、污染度、任务目标、脉冲扫描和
            特征线索。你的每个动作都会影响风险条、候选数量和最终得分。
          </p>
          <button
            className="action-button"
            onClick={() => {
              void startRound();
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
                void applyFreeze(region);
              }}
              onPulseScan={() => {
                void runPulseScan();
              }}
              onUseCard={(cardId) => {
                void applyCard(cardId);
              }}
              session={session}
            />
          </main>

          <GuessPanel
            disabled={controlsDisabled}
            labels={session.candidate_labels}
            missionTitle={session.mission_title}
            onConfirm={() => {
              void submitSelectedGuess();
            }}
            onSelect={setSelectedGuess}
            selectedGuess={selectedGuess}
          />

          <section className="panel result-panel">
            <div>
              <p className="eyebrow">本局状态</p>
              <h2>
                {session.status === "playing"
                  ? `${session.phase_label}：保持稳定并寻找最佳出手点`
                  : session.status === "won"
                    ? `识别成功：${session.revealed_target}`
                    : `识别失败：${session.revealed_target}`}
              </h2>
            </div>
            <p>当前任务：{session.mission_title}</p>
            <p>
              连胜：<strong>{session.combo}</strong>
            </p>
            <p>
              {session.signature_revealed
                ? `已捕获特征线索：${session.signature_clue}`
                : "尚未触发脉冲扫描，仍可主动缩小候选范围。"}
            </p>
          </section>
        </>
      )}
    </div>
  );
}
