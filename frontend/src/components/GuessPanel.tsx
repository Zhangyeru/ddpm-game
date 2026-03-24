import type { PendingActionKind } from "../game/types";

type GuessPanelProps = {
  busyAction: PendingActionKind | null;
  labels: string[];
  selectedGuess: string | null;
  disabled: boolean;
  guessReminder: string | null;
  missionTitle: string;
  onGuess: (label: string) => void;
};

export function GuessPanel({
  busyAction,
  labels,
  selectedGuess,
  disabled,
  guessReminder,
  missionTitle,
  onGuess
}: GuessPanelProps) {
  return (
    <section className="panel guess-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">候选目标</p>
          <h2>猜测台</h2>
        </div>
        <span className="tool-counter">
          {busyAction === "guess" && selectedGuess
            ? `提交中：${selectedGuess}`
            : "点击目标即提交"}
        </span>
      </div>

      <p className="guess-intro">
        当前候选 {labels.length} 项。{missionTitle} 点击任一候选后会直接作为本次猜测提交。
      </p>

      <div className="guess-grid">
        {labels.map((label) => (
          <button
            key={label}
            className={`guess-chip ${
              selectedGuess === label ? "guess-chip--active" : ""
            }`}
            disabled={disabled}
            onClick={() => onGuess(label)}
            type="button"
          >
            {busyAction === "guess" && selectedGuess === label ? "提交中..." : label}
          </button>
        ))}
      </div>

      {guessReminder ? (
        <div className="guess-warning" role="alert">
          <strong>选择错误</strong>
          <span>{guessReminder}</span>
        </div>
      ) : null}
    </section>
  );
}
