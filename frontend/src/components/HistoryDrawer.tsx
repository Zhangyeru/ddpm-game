import { useMemo, useState } from "react";
import { Drawer } from "./Drawer";
import { EmptyState } from "./EmptyState";
import { formatLevelCode } from "../game/levelPresentation";
import { ScoreBreakdownGrid } from "./ScoreBreakdownGrid";
import { ScoreEventList } from "./ScoreEventList";
import {
  breakdownItems,
  formatEndedAt,
  formatSignedScore
} from "../game/scorePresentation";
import type { ScoreHistoryEntry } from "../game/types";

type HistoryDrawerProps = {
  history: ScoreHistoryEntry[];
  onClose: () => void;
  open: boolean;
};

type HistoryFilter = "all" | "won" | "lost";
type HistorySort = "recent" | "score";

const FILTER_OPTIONS: Array<{ label: string; value: HistoryFilter }> = [
  { label: "全部", value: "all" },
  { label: "成功", value: "won" },
  { label: "失败", value: "lost" }
];

const SORT_OPTIONS: Array<{ label: string; value: HistorySort }> = [
  { label: "最近优先", value: "recent" },
  { label: "分数优先", value: "score" }
];

export function HistoryDrawer({
  history,
  onClose,
  open
}: HistoryDrawerProps) {
  const [searchValue, setSearchValue] = useState("");
  const [statusFilter, setStatusFilter] = useState<HistoryFilter>("all");
  const [sortBy, setSortBy] = useState<HistorySort>("recent");
  const [expandedSessionIds, setExpandedSessionIds] = useState<Set<string>>(
    () => new Set()
  );

  const filteredHistory = useMemo(() => {
    const normalizedSearch = searchValue.trim().toLowerCase();
    const next = history.filter((entry) => {
      const matchesStatus =
        statusFilter === "all" ? true : entry.status === statusFilter;
      const matchesSearch =
        normalizedSearch.length === 0
          ? true
          : `${entry.revealed_target ?? ""} ${entry.mission_title} ${entry.chapter_title ?? ""} ${entry.level_title ?? ""}`
              .toLowerCase()
              .includes(normalizedSearch);
      return matchesStatus && matchesSearch;
    });

    next.sort((left, right) => {
      if (sortBy === "score") {
        return right.final_score - left.final_score;
      }

      return right.ended_at.localeCompare(left.ended_at);
    });

    return next;
  }, [history, searchValue, sortBy, statusFilter]);

  const hasFilters = searchValue.trim().length > 0 || statusFilter !== "all" || sortBy !== "recent";
  const filteredExpandedCount = filteredHistory.filter((entry) =>
    expandedSessionIds.has(entry.session_id)
  ).length;
  const allFilteredExpanded =
    filteredHistory.length > 0 &&
    filteredExpandedCount === filteredHistory.length;
  const historyStats = useMemo(() => {
    if (history.length === 0) {
      return {
        averageScore: null,
        bestScore: null,
        lostCount: 0,
        wonCount: 0
      };
    }

    const wonCount = history.filter((entry) => entry.status === "won").length;
    const totalScore = history.reduce((sum, entry) => sum + entry.final_score, 0);
    const bestScore = history.reduce(
      (best, entry) => Math.max(best, entry.final_score),
      history[0].final_score
    );

    return {
      averageScore: Math.round(totalScore / history.length),
      bestScore,
      lostCount: history.length - wonCount,
      wonCount
    };
  }, [history]);

  function toggleEntry(sessionId: string, open: boolean) {
    setExpandedSessionIds((current) => {
      const next = new Set(current);
      if (open) {
        next.add(sessionId);
      } else {
        next.delete(sessionId);
      }
      return next;
    });
  }

  function setFilteredEntriesOpen(open: boolean) {
    setExpandedSessionIds((current) => {
      const next = new Set(current);
      filteredHistory.forEach((entry) => {
        if (open) {
          next.add(entry.session_id);
        } else {
          next.delete(entry.session_id);
        }
      });
      return next;
    });
  }

  return (
    <Drawer onClose={onClose} open={open} title="最近 10 局回收记录">
      <section className="history-toolbar">
        <label className="field">
          <span className="field__label">搜索目标或任务</span>
          <input
            className="field__input"
            onChange={(event) => setSearchValue(event.target.value)}
            placeholder="例如：猫、第二章、最终归档"
            type="search"
            value={searchValue}
          />
        </label>

        <div className="toolbar-block">
          <span className="field__label">状态筛选</span>
          <div className="chip-row">
            {FILTER_OPTIONS.map((option) => (
              <button
                key={option.value}
                className={`filter-chip ${
                  statusFilter === option.value ? "filter-chip--active" : ""
                }`}
                onClick={() => setStatusFilter(option.value)}
                type="button"
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>

        <div className="toolbar-block">
          <span className="field__label">排序方式</span>
          <div className="chip-row">
            {SORT_OPTIONS.map((option) => (
              <button
                key={option.value}
                className={`filter-chip ${
                  sortBy === option.value ? "filter-chip--active" : ""
                }`}
                onClick={() => setSortBy(option.value)}
                type="button"
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>
      </section>

      {history.length > 0 ? (
        <section className="history-stat-grid">
          <article className="history-stat-card">
            <span className="readout-label">成功</span>
            <strong>{historyStats.wonCount}</strong>
          </article>
          <article className="history-stat-card">
            <span className="readout-label">失败</span>
            <strong>{historyStats.lostCount}</strong>
          </article>
          <article className="history-stat-card">
            <span className="readout-label">最高分</span>
            <strong>
              {historyStats.bestScore === null
                ? "--"
                : formatSignedScore(historyStats.bestScore)}
            </strong>
          </article>
          <article className="history-stat-card">
            <span className="readout-label">平均分</span>
            <strong>
              {historyStats.averageScore === null
                ? "--"
                : formatSignedScore(historyStats.averageScore)}
            </strong>
          </article>
        </section>
      ) : null}

      <div className="drawer-summary-row">
        <div className="drawer-summary-copy">
          <span className="tool-counter">共 {history.length} 局</span>
          <span className="subtle-copy">
            当前结果：{filteredHistory.length} 条
          </span>
        </div>
        <div className="history-quick-actions">
          <button
            className="secondary-button compact-button"
            disabled={filteredHistory.length === 0 || allFilteredExpanded}
            onClick={() => setFilteredEntriesOpen(true)}
            type="button"
          >
            全部展开
          </button>
          <button
            className="secondary-button compact-button"
            disabled={filteredExpandedCount === 0}
            onClick={() => setFilteredEntriesOpen(false)}
            type="button"
          >
            全部收起
          </button>
        </div>
      </div>

      {history.length === 0 ? (
        <EmptyState
          detail="完成第一局后，这里会留下最近的回收记录，方便你回看目标、任务和得分变化。"
          eyebrow="暂无旧档"
          title="这里还没有留下记录"
        />
      ) : filteredHistory.length === 0 ? (
        <EmptyState
          action={
            hasFilters ? (
              <button
                className="secondary-button"
                onClick={() => {
                  setSearchValue("");
                  setStatusFilter("all");
                  setSortBy("recent");
                }}
                type="button"
              >
                清空筛选
              </button>
            ) : null
          }
          detail="试试清空关键词、切回全部状态，或者按最近时间重新查看。"
          eyebrow="未找到匹配"
          title="当前条件下没有可看的记录"
        />
      ) : (
        <div className="history-drawer-list">
          {filteredHistory.map((entry) => (
            <details
              className="history-item history-item--drawer"
              key={entry.session_id}
              onToggle={(event) => toggleEntry(entry.session_id, event.currentTarget.open)}
              open={expandedSessionIds.has(entry.session_id)}
            >
              <summary className="history-item__summary">
                <div>
                  <strong>
                    {entry.status === "won" ? "成功识别" : "失败回收"}：
                    {entry.revealed_target ?? "未知目标"}
                  </strong>
                  <span>
                    {`${entry.chapter && entry.level ? `${formatLevelCode(entry.chapter, entry.level)} ` : ""}${entry.level_title || "未知关卡"} · ${entry.mission_title} · ${formatEndedAt(entry.ended_at)}`}
                  </span>
                </div>
                <span
                  className={`score-delta ${
                    entry.final_score > 0
                      ? "score-delta--positive"
                      : entry.final_score < 0
                        ? "score-delta--negative"
                        : "score-delta--neutral"
                  }`}
                >
                  {formatSignedScore(entry.final_score)}
                </span>
              </summary>

              {entry.loss_reason ? (
                <p className="history-item__note">失败原因：{entry.loss_reason}</p>
              ) : null}

              {entry.score_breakdown ? (
                <ScoreBreakdownGrid compact items={breakdownItems(entry.score_breakdown)} />
              ) : null}

              <ScoreEventList
                emptyLabel="这一局没有留下分数变化记录。"
                events={entry.score_events}
              />
            </details>
          ))}
        </div>
      )}
    </Drawer>
  );
}
