import type { CardId, SessionSnapshot } from "../game/types";
import type { PendingActionKind } from "../game/types";
import {
  CARD_TOOL_GUIDE,
  RESOURCE_LIMITS
} from "../content/gameGuide";

type ToolPanelProps = {
  busyAction: PendingActionKind | null;
  session: SessionSnapshot | null;
  disabled: boolean;
  onUseCard: (cardId: CardId) => void;
};

const CARD_ORDER: readonly CardId[] = [
  "sharpen-outline",
  "mechanical-lens",
  "bio-scan"
];

export function ToolPanel({
  busyAction,
  session,
  disabled,
  onUseCard
}: ToolPanelProps) {
  const cardsRemaining = session?.cards_remaining ?? RESOURCE_LIMITS.cards;

  return (
    <section className="panel side-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">唯一工具</p>
          <h2>引导卡组</h2>
        </div>
        <span className="tool-counter">
          剩余 {cardsRemaining}/{RESOURCE_LIMITS.cards}
        </span>
      </div>

      <p className="tool-intro">
        只保留卡牌干预。先看主体家族，再用最值得的那一张。
      </p>

      <div className="tool-grid">
        {CARD_ORDER.map((cardId) => {
          const guide = CARD_TOOL_GUIDE[cardId];
          const used = session?.used_cards.includes(cardId) ?? false;
          const blocked =
            disabled ||
            !session ||
            session.status !== "playing" ||
            session.cards_remaining <= 0 ||
            used;

          return (
            <article
              key={cardId}
              className={`tool-card ${used ? "tool-card--used" : ""}`}
            >
              <div className="tool-card__header">
                <strong>{guide.title}</strong>
                <span className={`tool-badge ${used ? "tool-badge--used" : ""}`}>
                  {used ? "已使用" : "可用"}
                </span>
              </div>
              <p className="tool-card__summary">
                {guide.effect}
              </p>
              <p className="tool-card__hint">{guide.cost}</p>
              <p className="tool-card__hint tool-card__hint--secondary">
                {guide.timing}
              </p>
              <button
                className="tool-card__action"
                disabled={blocked}
                onClick={() => onUseCard(cardId)}
                type="button"
              >
                {used
                  ? "本局已用"
                  : busyAction === "card"
                    ? "应用中..."
                    : "立即使用"}
              </button>
            </article>
          );
        })}
      </div>
    </section>
  );
}
