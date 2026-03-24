import type { PendingActionKind } from "../game/types";

type GuessPanelProps = {
  busyAction: PendingActionKind | null;
  labels: string[];
  selectedGuess: string | null;
  disabled: boolean;
  missionTitle: string;
  onSelect: (label: string) => void;
  onConfirm: () => void;
};

export function GuessPanel({
  busyAction,
  labels,
  selectedGuess,
  disabled,
  missionTitle,
  onSelect,
  onConfirm
}: GuessPanelProps) {
  return (
    <section className="panel guess-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">候选目标</p>
          <h2>猜测台</h2>
        </div>
        <span className="tool-counter">
          {selectedGuess ?? "先选择一个目标"}
        </span>
      </div>

      <p className="guess-intro">
        当前候选 {labels.length} 项。{missionTitle}
      </p>

      <div className="guess-grid">
        {labels.map((label) => (
          <button
            key={label}
            className={`guess-chip ${
              selectedGuess === label ? "guess-chip--active" : ""
            }`}
            disabled={disabled}
            onClick={() => onSelect(label)}
            type="button"
          >
            {label}
          </button>
        ))}
      </div>

      <div className="guess-footer">
        <div className="guess-selection-card">
          <span className="readout-label">当前选择</span>
          <strong>{selectedGuess ?? "尚未选择"}</strong>
        </div>
        <button
          className="action-button guess-confirm"
          disabled={disabled || !selectedGuess}
          onClick={onConfirm}
          type="button"
        >
          {busyAction === "guess"
            ? "提交中..."
            : selectedGuess
              ? `确认：${selectedGuess}`
              : "先选择目标"}
        </button>
      </div>
    </section>
  );
}
