import type {
  FreezeRegionId,
  PendingActionKind,
  SessionSnapshot,
  TargetFamily
} from "../game/types";

type RulePanelProps = {
  busyAction: PendingActionKind | null;
  disabled: boolean;
  onCommitFamily: (family: TargetFamily) => void;
  onFreeze: (region: FreezeRegionId) => void;
  session: SessionSnapshot | null;
};

const FAMILY_OPTIONS: ReadonlyArray<{
  id: TargetFamily;
  label: string;
}> = [
  { id: "living", label: "生物" },
  { id: "machine", label: "机械" },
  { id: "structure", label: "建筑" }
];

const FREEZE_OPTIONS: ReadonlyArray<{
  id: FreezeRegionId;
  label: string;
}> = [
  { id: "upper-left", label: "左上" },
  { id: "center", label: "中央" },
  { id: "lower-right", label: "右下" }
];

export function RulePanel({
  busyAction,
  disabled,
  onCommitFamily,
  onFreeze,
  session
}: RulePanelProps) {
  if (!session) {
    return null;
  }

  const canCommitFamily =
    session.status === "playing" &&
    session.family_commit_required &&
    session.committed_family === null;
  const canFreeze =
    session.status === "playing" &&
    session.freeze_remaining > 0 &&
    session.frozen_region === null;

  return (
    <section className="panel side-panel rule-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">本关规则</p>
          <h2 className="tool-panel__title">规则提示</h2>
        </div>
        <span className="tool-counter">{session.rule_badges[0] ?? "规则已启用"}</span>
      </div>

      <p className="tool-intro">{session.rule_summary}</p>

      <div className="rule-pill-row">
        {session.rule_badges.map((badge) => (
          <span className="result-meta-chip" key={badge}>
            {badge}
          </span>
        ))}
      </div>

      {session.rule_status ? (
        <article className="result-card rule-panel__status">
          <span className="readout-label">规则状态</span>
          <strong>{session.rule_status}</strong>
        </article>
      ) : null}

      {canCommitFamily ? (
        <div className="rule-action-group">
          <span className="readout-label">先选目标家族</span>
          <div className="rule-action-grid">
            {FAMILY_OPTIONS.map((family) => (
              <button
                className="secondary-button"
                disabled={disabled || busyAction === "commit-family"}
                key={family.id}
                onClick={() => onCommitFamily(family.id)}
                type="button"
              >
                {busyAction === "commit-family" ? "提交中..." : family.label}
              </button>
            ))}
          </div>
        </div>
      ) : null}

      {canFreeze ? (
        <div className="rule-action-group">
          <span className="readout-label">选择冻结区域</span>
          <div className="rule-action-grid">
            {FREEZE_OPTIONS.map((region) => (
              <button
                className="secondary-button"
                disabled={disabled || busyAction === "freeze"}
                key={region.id}
                onClick={() => onFreeze(region.id)}
                type="button"
              >
                {busyAction === "freeze" ? "冻结中..." : region.label}
              </button>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}
