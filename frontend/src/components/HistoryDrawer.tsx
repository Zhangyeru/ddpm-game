import { useMemo, useState } from "react";
import { Drawer } from "./Drawer";
import { EmptyState } from "./EmptyState";
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

  return (
    <Drawer onClose={onClose} open={open} title="最近 10 局回收记录">
      <section className="history-toolbar">
        <label className="field">
          <span className="field__label">搜索目标或任务</span>
          <input
            className="field__input"
            onChange={(event) => setSearchValue(event.target.value)}
            placeholder="例如：猫、第二章、终端审判"
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

      <div className="drawer-summary-row">
        <span className="tool-counter">共 {history.length} 局</span>
        <span className="subtle-copy">
          当前结果：{filteredHistory.length} 条
        </span>
      </div>

      {history.length === 0 ? (
        <EmptyState
          detail="完成第一局后，这里会保存本地回收记录，方便你按目标、任务和分数回看打法。"
          eyebrow="历史为空"
          title="还没有回收记录"
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
          detail="试试清空关键词、切回全部状态，或者按最近时间排序。"
          eyebrow="没有匹配项"
          title="当前条件下没有记录"
        />
      ) : (
        <div className="history-drawer-list">
          {filteredHistory.map((entry) => (
            <details className="history-item history-item--drawer" key={entry.session_id}>
              <summary className="history-item__summary">
                <div>
                  <strong>
                    {entry.status === "won" ? "成功识别" : "失败回收"}：
                    {entry.revealed_target ?? "未知目标"}
                  </strong>
                  <span>
                    {`${entry.chapter && entry.level ? `第 ${entry.chapter}-${entry.level} 关 ` : ""}${entry.level_title || "未知关卡"} · ${entry.mission_title} · ${formatEndedAt(entry.ended_at)}`}
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
                emptyLabel="这局没有记录到分数事件。"
                events={entry.score_events}
              />
            </details>
          ))}
        </div>
      )}
    </Drawer>
  );
}
