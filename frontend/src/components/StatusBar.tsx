import type { SessionSnapshot } from "../game/types";

type StatusBarProps = {
  session: SessionSnapshot | null;
  busy: boolean;
  onStart: () => void;
};

export function StatusBar({
  session,
  busy,
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

  return (
    <header className="status-bar panel">
      <div className="title-block">
        <p className="eyebrow">DDPM 网页游戏原型</p>
        <h1>噪声考古学家</h1>
        <p className="subtle-copy">
          把一段去噪过程变成可观察、可干预、可抢答的一局游戏。
        </p>
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
            {session ? `${session.time_remaining} 秒` : "--"}
          </strong>
        </div>
        <div className="stat-card">
          <span className="stat-label">分数</span>
          <strong className="stat-value">
            {session ? session.score : "--"}
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
        <button
          className="action-button"
          onClick={onStart}
          disabled={busy}
          type="button"
        >
          {session ? "重新开局" : "启动扫描"}
        </button>
      </div>
    </header>
  );
}
