import { useMemo, useState } from "react";
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

type LeaderboardFilter = "all" | "complete" | "active";

const LEADERBOARD_FILTERS: Array<{ label: string; value: LeaderboardFilter }> = [
  { label: "全部", value: "all" },
  { label: "已通关", value: "complete" },
  { label: "推进中", value: "active" }
];

export function LeaderboardPanel({
  authUser,
  entries,
  error,
  loading,
  onRetry
}: LeaderboardPanelProps) {
  const currentUserId = authUser?.id ?? null;
  const [searchValue, setSearchValue] = useState("");
  const [filter, setFilter] = useState<LeaderboardFilter>("all");

  const currentUserEntry = useMemo(
    () => entries.find((entry) => entry.user_id === currentUserId) ?? null,
    [currentUserId, entries]
  );

  const filteredEntries = useMemo(() => {
    const normalizedSearch = searchValue.trim().toLowerCase();
    return entries.filter((entry) => {
      const matchesSearch =
        normalizedSearch.length === 0
          ? true
          : entry.username.toLowerCase().includes(normalizedSearch);
      const matchesFilter =
        filter === "all"
          ? true
          : filter === "complete"
            ? entry.campaign_complete
            : !entry.campaign_complete;
      return matchesSearch && matchesFilter;
    });
  }, [entries, filter, searchValue]);

  const hasFilters = searchValue.trim().length > 0 || filter !== "all";

  return (
    <section className="panel landing-panel leaderboard-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">总分排行</p>
          <h2>全部账号</h2>
        </div>
        <div className="panel-heading__actions">
          <span className="tool-counter">
            {currentUserEntry ? `你排第 ${currentUserEntry.rank}` : "仅账号上榜"}
          </span>
          <button
            className="secondary-button compact-button"
            disabled={loading}
            onClick={onRetry}
            type="button"
          >
            {loading ? "刷新中..." : "刷新"}
          </button>
        </div>
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
          detail="现在还没有账号成绩写入总榜。登录并完成至少一关后，这里就会出现第一批排行。"
          eyebrow="总榜未开"
          title="这里还没有可显示的成绩"
        />
      ) : (
        <>
          <section className="leaderboard-toolbar">
            <label className="field">
              <span className="field__label">搜索账号</span>
              <input
                className="field__input"
                onChange={(event) => setSearchValue(event.target.value)}
                placeholder="输入用户名"
                type="search"
                value={searchValue}
              />
            </label>

            <div className="toolbar-block">
              <span className="field__label">榜单范围</span>
              <div className="chip-row">
                {LEADERBOARD_FILTERS.map((option) => (
                  <button
                    key={option.value}
                    className={`filter-chip ${
                      filter === option.value ? "filter-chip--active" : ""
                    }`}
                    onClick={() => setFilter(option.value)}
                    type="button"
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>
          </section>

          <div className="drawer-summary-row leaderboard-summary-row">
            <span className="tool-counter">当前结果 {filteredEntries.length}</span>
            <span className="subtle-copy">
              {entries.length > 0 ? `总计 ${entries.length} 个账号` : "暂无账号"}
            </span>
          </div>

          {filteredEntries.length === 0 ? (
            <EmptyState
              action={
                hasFilters ? (
                  <button
                    className="secondary-button"
                    onClick={() => {
                      setSearchValue("");
                      setFilter("all");
                    }}
                    type="button"
                  >
                    清空筛选
                  </button>
                ) : null
              }
              detail="试试清空用户名关键词，或者切回全部范围查看。"
              eyebrow="未找到账号"
              title="当前条件下没有排行记录"
            />
          ) : (
            <div className="leaderboard-list">
              {filteredEntries.map((entry) => {
                const isCurrentUser = currentUserId !== null && entry.user_id === currentUserId;
                return (
                  <article
                    key={entry.user_id}
                    aria-current={isCurrentUser ? "true" : undefined}
                    className={`leaderboard-item ${
                      isCurrentUser ? "leaderboard-item--active" : ""
                    } ${entry.rank <= 3 ? "leaderboard-item--podium" : ""}`}
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

          {currentUserEntry ? (
            <article className="leaderboard-current-card">
              <span className="readout-label">你的榜单位置</span>
              <strong>{`第 ${currentUserEntry.rank} 名 · ${formatSignedScore(
                currentUserEntry.campaign_total_score
              )}`}</strong>
              <p>
                {currentUserEntry.campaign_complete
                  ? "整套档案已通关，继续重刷单关最佳分可以提高总分。"
                  : `还差 ${12 - currentUserEntry.completed_count} 关完成整套档案。`}
              </p>
            </article>
          ) : null}
        </>
      )}
    </section>
  );
}
