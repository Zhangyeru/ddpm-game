import type { ScoreEvent } from "../game/types";
import { formatSignedScore } from "../game/scorePresentation";

type ScoreEventListProps = {
  emptyLabel: string;
  events: ScoreEvent[];
  limit?: number;
};

export function ScoreEventList({
  emptyLabel,
  events,
  limit
}: ScoreEventListProps) {
  const visibleEvents = [...events].reverse().slice(0, limit ?? events.length);

  if (visibleEvents.length === 0) {
    return <p className="result-note">{emptyLabel}</p>;
  }

  return (
    <ul className="score-ledger">
      {visibleEvents.map((entry, index) => (
        <li className="score-event" key={`${entry.kind}-${entry.title}-${index}`}>
          <div className="score-event__header">
            <strong>{entry.title}</strong>
            <span
              className={`score-delta ${
                entry.delta > 0
                  ? "score-delta--positive"
                  : entry.delta < 0
                    ? "score-delta--negative"
                    : "score-delta--neutral"
              }`}
            >
              {formatSignedScore(entry.delta)}
            </span>
          </div>
          <p>{entry.detail}</p>
          <span>当前累计：{entry.running_score}</span>
        </li>
      ))}
    </ul>
  );
}
