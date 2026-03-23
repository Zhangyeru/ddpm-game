type GuessPanelProps = {
  labels: string[];
  selectedGuess: string | null;
  disabled: boolean;
  missionTitle: string;
  onSelect: (label: string) => void;
  onConfirm: () => void;
};

export function GuessPanel({
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
      </div>

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
        <p>
          当前候选 {labels.length} 项。{missionTitle}
        </p>
        <button
          className="action-button"
          disabled={disabled || !selectedGuess}
          onClick={onConfirm}
          type="button"
        >
          确认猜测
        </button>
      </div>
    </section>
  );
}
