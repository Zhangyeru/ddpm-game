import { EmptyState } from "./EmptyState";
import { formatSignedScore } from "../game/scorePresentation";
import type { AuthUser, LeaderboardEntry } from "../game/types";

type LeaderboardPanelProps = {
  authUser: AuthUser | null;
  entries: LeaderboardEntry[];
  error: string | null;
  loading: boolean;
  onRetry: () => void;
};

export function LeaderboardPanel({
  authUser,
  entries,
  error,
  loading,
  onRetry
}: LeaderboardPanelProps) {
  const currentUserId = authUser?.id ?? null;

  return (
    <section className="panel landing-panel leaderboard-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">总分排行</p>
          <h2>全部账号</h2>
        </div>
        <span className="tool-counter">仅账号上榜</span>
      </div>

      {loading ? (
        <div className="leaderboard-list leaderboard-list--skeleton" aria-hidden="true">
          {Array.from({ length: 5 }).map((_, index) => (
            <div className="leaderboard-item leaderboard-item--skeleton" key={index}>
              <span className="leaderboard-rank skeleton" />
              <div className="leaderboard-meta">
                <span className="skeleton leaderboard-skeleton leaderboard-skeleton--title" />
                <span className="skeleton leaderboard-skeleton leaderboard-skeleton--meta" />
              </div>
              <span className="skeleton leaderboard-skeleton leaderboard-skeleton--score" />
            </div>
          ))}
        </div>
      ) : error ? (
        <EmptyState
          action={
            <button className="secondary-button" onClick={onRetry} type="button">
              重试加载
            </button>
          }
          detail={`${error} 你可以稍后再试，或先登录并完成一关，让成绩写入总榜。`}
          eyebrow="总榜暂不可用"
          title="眼下还无法读取总分排行"
        />
      ) : entries.length === 0 ? (
        <EmptyState
          detail="现在还没有账号成绩写入总榜。登录并完成至少一关后，这里就会出现排行。"
          eyebrow="总榜未开"
          title="这里还没有可显示的成绩"
        />
      ) : (
        <div className="leaderboard-list">
          {entries.map((entry) => {
            const isCurrentUser = currentUserId !== null && entry.user_id === currentUserId;
            return (
              <article
                key={entry.user_id}
                className={`leaderboard-item ${
                  isCurrentUser ? "leaderboard-item--active" : ""
                }`}
              >
                <span className="leaderboard-rank">{entry.rank}</span>
                <div className="leaderboard-meta">
                  <strong>
                    {entry.username}
                    {isCurrentUser ? " · 你" : ""}
                  </strong>
                  <span>
                    {entry.campaign_complete
                      ? `12/12 关已完成`
                      : `已完成 ${entry.completed_count}/12 关`}
                  </span>
                </div>
                <strong className="leaderboard-score">
                  {formatSignedScore(entry.campaign_total_score)}
                </strong>
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
