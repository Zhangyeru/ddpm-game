import type { ScoreBreakdownItem } from "../game/scorePresentation";
import { formatSignedScore } from "../game/scorePresentation";

type ScoreBreakdownGridProps = {
  compact?: boolean;
  items: ScoreBreakdownItem[];
  summary?: boolean;
};

export function ScoreBreakdownGrid({
  compact = false,
  items,
  summary = false
}: ScoreBreakdownGridProps) {
  return (
    <div
      className={`breakdown-grid ${compact ? "breakdown-grid--compact" : ""} ${
        summary ? "breakdown-grid--summary" : ""
      }`}
    >
      {items.map((item) => (
        <div className="breakdown-row" key={item.label}>
          <span>{item.label}</span>
          <strong>{formatSignedScore(item.value)}</strong>
        </div>
      ))}
    </div>
  );
}
