import type {
  AuthUser,
  PendingActionKind,
  ProgressSnapshot,
  SessionSnapshot
} from "../game/types";
import { describeLivePriority } from "../content/gameGuide";
import { formatLevelCode } from "../game/levelPresentation";
import { formatSignedScore } from "../game/scorePresentation";

type StatusBarProps = {
  authBusyAction: Extract<PendingActionKind, "login" | "logout" | "register"> | null;
  authUser: AuthUser | null;
  busyAction: PendingActionKind | null;
  historyCount: number;
  leaderboardOpen: boolean;
  onOpenLeaderboard: () => void;
  onOpenHistory: () => void;
  onLogout: () => void;
  progression: ProgressSnapshot | null;
  session: SessionSnapshot | null;
  onStart: () => void;
};

export function StatusBar({
  authBusyAction,
  authUser,
  busyAction,
  historyCount,
  leaderboardOpen,
  onOpenLeaderboard,
  onOpenHistory,
  onLogout,
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
      ? `${progressLevel.summary} 本关目标：${progressLevel.mission_title}。`
      : "看清目标、谨慎出卡、尽早提交。详细规则见首页。";
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
        <p className="eyebrow">异象档案回收</p>
        <h1>逆噪显影</h1>
        <p className="subtle-copy">{leadCopy}</p>
        <div className="title-chip-row">
          <span className="title-chip">
            {session
              ? `${session.chapter_title} · ${session.level_title}`
              : progressLevel
                ? `${progressLevel.chapter_title} · ${progressLevel.level_title}`
                : "12 关逐步推进"}
          </span>
          <span className="title-chip title-chip--accent">
            {session
              ? session.mission_title
              : progressLevel?.mission_title ?? "继续推进当前关卡"}
          </span>
          {authUser ? (
            <span className="title-chip">{`已登录 · ${authUser.username}`}</span>
          ) : (
            <span className="title-chip">本地存档</span>
          )}
        </div>
      </div>

      <div className="stats-grid">
        <div className="stat-card">
          <span className="stat-label">关卡</span>
          <strong className="stat-value">
            {session
              ? formatLevelCode(session.chapter, session.level)
              : progressLevel
                ? formatLevelCode(progressLevel.chapter, progressLevel.level)
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
          <span className="stat-label">{session ? "当前分数" : "总分"}</span>
          <strong className="stat-value">
            {session
              ? formatSignedScore(session.score)
              : progression
                ? formatSignedScore(progression.campaign_total_score)
                : "--"}
          </strong>
        </div>
        <div className="stat-card">
          <span className="stat-label">{session ? "累计分数" : "猜测"}</span>
          <strong className="stat-value">
            {session
              ? progression
                ? formatSignedScore(progression.campaign_total_score)
                : "--"
              : progressLevel
                ? `${progressLevel.max_guesses} 次`
                : "--"}
          </strong>
        </div>
        <div className="stat-card">
          <span className="stat-label">{session ? "稳定度" : "卡牌"}</span>
          <strong className="stat-value">
            {session ? session.stability : progressLevel ? `${progressLevel.max_cards} 张` : "--"}
          </strong>
        </div>
      </div>

      <div className="session-actions">
        <span className={`status-pill status-pill--${statusKey}`}>
          {statusLabel}
        </span>
        <div className="session-action-row">
          <div className="session-nav-stack">
            <button
              className="secondary-button"
              onClick={onOpenLeaderboard}
              type="button"
            >
              {leaderboardOpen ? "返回主界面" : "总分排行"}
            </button>
            <button
              className="secondary-button"
              onClick={onOpenHistory}
              type="button"
            >
              历史记录 {historyCount > 0 ? `(${historyCount})` : ""}
            </button>
          </div>
          {authUser ? (
            <button
              className="secondary-button"
              disabled={authBusyAction === "logout"}
              onClick={onLogout}
              type="button"
            >
              {authBusyAction === "logout" ? "退出中..." : "退出登录"}
            </button>
          ) : null}
          <button
            className="action-button"
            onClick={onStart}
            disabled={busyAction !== null || authBusyAction !== null}
            type="button"
          >
            {actionLabel}
          </button>
        </div>
      </div>
    </header>
  );
}
