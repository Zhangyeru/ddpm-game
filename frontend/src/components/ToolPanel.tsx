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
  onPulseScan: () => void;
};

export function ToolPanel({
  session,
  disabled,
  onUseCard,
  onFreeze,
  onPulseScan
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
        <p className="section-label">主动技能</p>
        <div className="tool-grid">
          <button
            className="tool-card tool-card--accent"
            disabled={
              disabled ||
              !session ||
              session.status !== "playing" ||
              session.scan_charges <= 0
            }
            onClick={onPulseScan}
            type="button"
          >
            <strong>脉冲扫描</strong>
            <span>
              暴露特征线索并缩小候选范围，但会拉高污染度。
            </span>
          </button>
        </div>
      </div>

      <div className="tool-section">
        <p className="section-label">引导卡</p>
        <div className="tool-grid">
          {(session?.card_options ?? []).map((card) => {
            const used = session?.used_cards.includes(card.id) ?? false;
            const blocked =
              disabled ||
              !session ||
              session.status !== "playing" ||
              session.cards_remaining <= 0 ||
              used;

            return (
              <button
                key={card.id}
                className={`tool-card ${used ? "tool-card--used" : ""}`}
                disabled={blocked}
                onClick={() => onUseCard(card.id)}
                type="button"
              >
                <strong>{card.title}</strong>
                <span>{card.summary}</span>
              </button>
            );
          })}
        </div>
      </div>

      <div className="tool-section">
        <p className="section-label">冻结区域</p>
        <div className="tool-grid">
          {(session?.freeze_region_options ?? []).map((regionOption) => {
            const selected = session?.frozen_region === regionOption.id;
            const blocked =
              disabled ||
              !session ||
              session.status !== "playing" ||
              !session.freeze_available;

            return (
              <button
                key={regionOption.id}
                className={`tool-card ${selected ? "tool-card--used" : ""}`}
                disabled={blocked}
                onClick={() => onFreeze(regionOption.id)}
                type="button"
              >
                <strong>{regionOption.title}</strong>
                <span>{regionOption.summary}</span>
              </button>
            );
          })}
        </div>
      </div>
    </section>
  );
}
