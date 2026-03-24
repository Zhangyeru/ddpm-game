import type { PendingActionKind, SessionSnapshot } from "../game/types";
import { describeLivePriority } from "../content/gameGuide";

type StatusBarProps = {
  busyAction: PendingActionKind | null;
  historyCount: number;
  onOpenHistory: () => void;
  session: SessionSnapshot | null;
  onStart: () => void;
};

export function StatusBar({
  busyAction,
  historyCount,
  onOpenHistory,
  session,
  onStart
}: StatusBarProps) {
  const statusKey = session?.status ?? "idle";
  const statusLabel = session
    ? session.status === "playing"
      ? "解码中"
      : session.status === "won"
        ? "已识别"
        : "失败"
    : "待机";
  const leadCopy = session
    ? describeLivePriority(session)
    : "观察图像、谨慎出卡、尽早提交。完整规则保留在首页。";

  return (
    <header className="status-bar panel">
      <div className="title-block">
        <p className="eyebrow">DDPM 网页游戏原型</p>
        <h1>噪声考古学家</h1>
        <p className="subtle-copy">{leadCopy}</p>
        <div className="title-chip-row">
          <span className="title-chip">
            {session ? session.mission_title : "完整规则页已就绪"}
          </span>
          <span className="title-chip title-chip--accent">
            {session ? session.threat_label : "准备开始"}
          </span>
        </div>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <span className="stat-label">章节</span>
          <strong className="stat-value">
            {session ? `${session.chapter}-${session.level}` : "--"}
          </strong>
        </div>
        <div className="stat-card">
          <span className="stat-label">时间</span>
          <strong className="stat-value">
            {session ? `${session.seconds_remaining.toFixed(1)} 秒` : "--"}
          </strong>
        </div>
        <div className="stat-card">
          <span className="stat-label">分数</span>
          <strong className="stat-value">
            {session ? session.score : "--"}
          </strong>
        </div>
        <div className="stat-card">
          <span className="stat-label">稳定度</span>
          <strong className="stat-value">
            {session ? session.stability : "--"}
          </strong>
        </div>
        <div className="stat-card">
          <span className="stat-label">污染度</span>
          <strong className="stat-value">
            {session ? session.corruption : "--"}
          </strong>
        </div>
        <div className="stat-card">
          <span className="stat-label">状态</span>
          <strong className="stat-value">{statusLabel}</strong>
        </div>
      </div>

      <div className="session-actions">
        <span
          className={`status-pill status-pill--${statusKey}`}
        >
          {statusLabel}
        </span>
        <div className="session-action-row">
          <button
            className="secondary-button"
            onClick={onOpenHistory}
            type="button"
          >
            历史记录 {historyCount > 0 ? `(${historyCount})` : ""}
          </button>
          <button
            className="action-button"
            onClick={onStart}
            disabled={busyAction !== null}
            type="button"
          >
            {busyAction === "start"
              ? "启动中..."
              : session
                ? "重新开局"
                : "启动扫描"}
          </button>
        </div>
      </div>
    </header>
  );
}
