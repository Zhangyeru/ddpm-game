import { LeaderboardPanel } from "./LeaderboardPanel";
import { formatSignedScore } from "../game/scorePresentation";
import type { AuthUser, LeaderboardEntry, ProgressSnapshot } from "../game/types";

type LeaderboardPageProps = {
  authUser: AuthUser | null;
  entries: LeaderboardEntry[];
  error: string | null;
  loading: boolean;
  onBack: () => void;
  onRetry: () => void;
  progression: ProgressSnapshot | null;
};

export function LeaderboardPage({
  authUser,
  entries,
  error,
  loading,
  onBack,
  onRetry,
  progression
}: LeaderboardPageProps) {
  return (
    <section className="leaderboard-page">
      <section className="panel leaderboard-page__hero">
        <div className="leaderboard-page__copy">
          <p className="eyebrow">排行榜</p>
          <h2>账号总分榜</h2>
          <p>
            排名按闯关总分排序，同分时优先已完成更多关卡的账号。只有注册账号会上榜，游客试玩不会写入排行。
          </p>
          <div className="hero-pill-row">
            <span className="hero-pill">显示全部账号</span>
            <span className="hero-pill">按各关最佳分累计</span>
            {progression ? (
              <span className="hero-pill">
                {`你的总分 ${formatSignedScore(progression.campaign_total_score)}`}
              </span>
            ) : null}
          </div>
        </div>

        <div className="leaderboard-page__actions">
          <button className="secondary-button" onClick={onBack} type="button">
            返回主界面
          </button>
        </div>
      </section>

      <div className="leaderboard-page__grid">
        <LeaderboardPanel
          authUser={authUser}
          entries={entries}
          error={error}
          loading={loading}
          onRetry={onRetry}
        />

        <section className="panel landing-panel leaderboard-page__notes">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">当前状态</p>
              <h2>{authUser ? "你的账号" : "上榜说明"}</h2>
            </div>
            {authUser ? <span className="tool-counter">{authUser.username}</span> : null}
          </div>

          {authUser && progression ? (
            <div className="landing-stack">
              <article className="landing-card">
                <strong>当前排名依据</strong>
                <p>{`闯关总分 ${formatSignedScore(progression.campaign_total_score)}`}</p>
                <span>{`已完成 ${progression.completed_count}/${progression.total_levels} 关`}</span>
              </article>
              <article className="landing-card">
                <strong>提升方式</strong>
                <p>继续推进未完成关卡，或者重刷已有关卡的最佳分。</p>
                <span>排行榜只记录每关最佳分，不会因为重复通关无限累加。</span>
              </article>
            </div>
          ) : (
            <div className="landing-stack">
              <article className="landing-card">
                <strong>为什么游客不在榜单里</strong>
                <p>排行榜只统计已注册账号的持久成绩，避免临时玩家 ID 造成重复榜单数据。</p>
                <span>登录或注册后，完成一关即可开始参与总分排行。</span>
              </article>
              <article className="landing-card">
                <strong>总分如何计算</strong>
                <p>每关只保留历史最佳分，12 关最佳分相加后形成闯关总分。</p>
                <span>失败局如果分数更高，也可以刷新该关最佳。</span>
              </article>
            </div>
          )}
        </section>
      </div>
    </section>
  );
}
