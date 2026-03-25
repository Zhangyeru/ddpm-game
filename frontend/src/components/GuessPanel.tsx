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
  const hiddenCount = labels.filter((label) => label === "未知信号").length;

  return (
    <section className="panel guess-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">可选目标</p>
          <h2>提交猜测</h2>
        </div>
        <span className="tool-counter">
          {busyAction === "guess" && selectedGuess
            ? `提交中：${selectedGuess}`
            : "点击目标即提交"}
        </span>
      </div>

      <p className="guess-intro">
        当前候选 {labels.length} 项{hiddenCount > 0 ? `，其中 ${hiddenCount} 项尚未解锁` : ""}。{missionTitle} 点击任一已显露候选后会直接作为本次猜测提交。
      </p>

      <div className="guess-grid">
        {labels.map((label, index) => (
          <button
            key={`${label}-${index}`}
            className={`guess-chip ${
              selectedGuess === label ? "guess-chip--active" : ""
            }`}
            disabled={disabled || label === "未知信号"}
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
