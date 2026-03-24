import type {
  PendingActionKind,
  ProgressSnapshot,
  SessionSnapshot
} from "../game/types";
import { describeLivePriority } from "../content/gameGuide";

type StatusBarProps = {
  busyAction: PendingActionKind | null;
  historyCount: number;
  onOpenHistory: () => void;
  progression: ProgressSnapshot | null;
  session: SessionSnapshot | null;
  onStart: () => void;
};

export function StatusBar({
  busyAction,
  historyCount,
  onOpenHistory,
  progression,
  session,
  onStart
}: StatusBarProps) {
  const progressLevel = progression?.current_level ?? null;
  const statusKey = session?.status ?? "idle";
  const statusLabel = session
    ? session.status === "playing"
      ? "解码中"
      : session.status === "won"
        ? "已识别"
        : "失败"
    : progression?.campaign_complete
      ? "已通关"
      : "待机";
  const leadCopy = session
    ? describeLivePriority(session)
    : progressLevel
      ? `${progressLevel.summary} 当前任务：${progressLevel.mission_title}。`
      : "观察图像、谨慎出卡、尽早提交。完整规则保留在首页。";
  const actionLabel =
    busyAction === "start"
      ? "载入中..."
      : session
        ? "重试本关"
        : progression?.campaign_complete
          ? "重开第一关"
          : progression?.completed_count
            ? "继续当前关"
            : "开始第一关";

  return (
    <header className="status-bar panel">
      <div className="title-block">
        <p className="eyebrow">DDPM 网页游戏原型</p>
        <h1>噪声考古学家</h1>
        <p className="subtle-copy">{leadCopy}</p>
        <div className="title-chip-row">
          <span className="title-chip">
            {session
              ? `${session.chapter_title} · ${session.level_title}`
              : progressLevel
                ? `${progressLevel.chapter_title} · ${progressLevel.level_title}`
                : "12 关线性闯关"}
          </span>
          <span className="title-chip title-chip--accent">
            {session
              ? session.mission_title
              : progressLevel?.mission_title ?? "继续推进当前关卡"}
          </span>
        </div>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <span className="stat-label">关卡</span>
          <strong className="stat-value">
            {session
              ? `第 ${session.chapter}-${session.level} 关`
              : progressLevel
                ? `第 ${progressLevel.chapter}-${progressLevel.level} 关`
                : "--"}
          </strong>
        </div>
        <div className="stat-card">
          <span className="stat-label">进度</span>
          <strong className="stat-value">
            {progression
              ? `${progression.completed_count}/${progression.total_levels}`
              : "--"}
          </strong>
        </div>
        <div className="stat-card">
          <span className="stat-label">{session ? "时间" : "候选"}</span>
          <strong className="stat-value">
            {session
              ? `${session.seconds_remaining.toFixed(1)} 秒`
              : progressLevel
                ? `${progressLevel.candidate_count} 项`
                : "--"}
          </strong>
        </div>
        <div className="stat-card">
          <span className="stat-label">{session ? "分数" : "猜测"}</span>
          <strong className="stat-value">
            {session ? session.score : progressLevel ? `${progressLevel.max_guesses} 次` : "--"}
          </strong>
        </div>
        <div className="stat-card">
          <span className="stat-label">{session ? "稳定度" : "卡牌"}</span>
          <strong className="stat-value">
            {session ? session.stability : progressLevel ? `${progressLevel.max_cards} 张` : "--"}
          </strong>
        </div>
        <div className="stat-card">
          <span className="stat-label">状态</span>
          <strong className="stat-value">{statusLabel}</strong>
        </div>
      </div>

      <div className="session-actions">
        <span className={`status-pill status-pill--${statusKey}`}>
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
            {actionLabel}
          </button>
        </div>
      </div>
    </header>
  );
}
