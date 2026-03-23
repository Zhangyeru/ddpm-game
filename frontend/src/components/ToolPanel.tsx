import { CARD_COPY, FREEZE_COPY } from "../game/config";
import type {
  CardId,
  FreezeRegion,
  SessionSnapshot
} from "../game/types";

type ToolPanelProps = {
  session: SessionSnapshot | null;
  disabled: boolean;
  onUseCard: (cardId: CardId) => void;
  onFreeze: (region: FreezeRegion) => void;
};

export function ToolPanel({
  session,
  disabled,
  onUseCard,
  onFreeze
}: ToolPanelProps) {
  return (
    <section className="panel side-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">干预工具</p>
          <h2>工具架</h2>
        </div>
      </div>

      <div className="tool-section">
        <p className="section-label">引导卡</p>
        <div className="tool-grid">
          {(
            Object.entries(CARD_COPY) as Array<
              [CardId, (typeof CARD_COPY)[CardId]]
            >
          ).map(([cardId, copy]) => {
            const used = session?.used_cards.includes(cardId) ?? false;
            const blocked =
              disabled ||
              !session ||
              session.status !== "playing" ||
              session.cards_remaining <= 0 ||
              used;

            return (
              <button
                key={cardId}
                className={`tool-card ${used ? "tool-card--used" : ""}`}
                disabled={blocked}
                onClick={() => onUseCard(cardId)}
                type="button"
              >
                <strong>{copy.title}</strong>
                <span>{copy.summary}</span>
              </button>
            );
          })}
        </div>
      </div>

      <div className="tool-section">
        <p className="section-label">冻结区域</p>
        <div className="tool-grid">
          {(
            Object.entries(FREEZE_COPY) as Array<
              [FreezeRegion, (typeof FREEZE_COPY)[FreezeRegion]]
            >
          ).map(([region, copy]) => {
            const selected = session?.frozen_region === region;
            const blocked =
              disabled ||
              !session ||
              session.status !== "playing" ||
              !session.freeze_available;

            return (
              <button
                key={region}
                className={`tool-card ${selected ? "tool-card--used" : ""}`}
                disabled={blocked}
                onClick={() => onFreeze(region)}
                type="button"
              >
                <strong>{copy.title}</strong>
                <span>{copy.summary}</span>
              </button>
            );
          })}
        </div>
      </div>
    </section>
  );
}
