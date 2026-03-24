import type { CardId, SessionSnapshot } from "../game/types";
import type { PendingActionKind } from "../game/types";
import { CARD_TOOL_GUIDE } from "../content/gameGuide";

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

const CARD_FAMILY_LABEL: Record<CardId, string> = {
  "sharpen-outline": "通用稳像",
  "mechanical-lens": "机械 / 建筑",
  "bio-scan": "生物目标"
};

export function ToolPanel({
  busyAction,
  session,
  disabled,
  onUseCard
}: ToolPanelProps) {
  const cardsRemaining = session?.cards_remaining ?? 0;
  const maxCards = session?.max_cards ?? 0;

  return (
    <section className="panel side-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">唯一工具</p>
          <h2 className="tool-panel__title">引导卡组</h2>
        </div>
        <span className="tool-counter">
          {session ? `剩余 ${cardsRemaining}/${maxCards}` : "等待开局"}
        </span>
      </div>

      <p className="tool-intro">
        先看主体家族，再决定是否出卡。
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
                  {used ? "已使用" : CARD_FAMILY_LABEL[cardId]}
                </span>
              </div>
              <div className="tool-card__body">
                <span className="tool-card__line">
                  <strong>效果</strong>
                  {guide.effect}
                </span>
                <span className="tool-card__line">
                  <strong>代价</strong>
                  {guide.cost}
                </span>
                <span className="tool-card__line">
                  <strong>适合</strong>
                  {guide.timing}
                </span>
              </div>
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
