import { describeMissionFocus } from "../content/gameGuide";
import { formatLevelCode } from "../game/levelPresentation";
import { ScoreBreakdownGrid } from "./ScoreBreakdownGrid";
import { ScoreEventList } from "./ScoreEventList";
import {
  summaryBreakdownItems,
  formatSignedScore,
  breakdownItems
} from "../game/scorePresentation";
import type {
  PendingActionKind,
  ProgressSnapshot,
  SessionSnapshot
} from "../game/types";

type ScorePanelProps = {
  busyAction: PendingActionKind | null;
  historyCount: number;
  onAdvance: () => void;
  onOpenHistory: () => void;
  onRetryLevel: () => void;
  progression: ProgressSnapshot | null;
  session: SessionSnapshot;
};

export function ScorePanel({
  busyAction,
  historyCount,
  onAdvance,
  onOpenHistory,
  onRetryLevel,
  progression,
  session
}: ScorePanelProps) {
  const breakdown = session.score_breakdown;
  const isFinished = session.status !== "playing";

  if (!isFinished) {
    return (
      <section className="panel result-panel result-panel--live">
        <div className="panel-heading result-panel__hero result-panel__hero--live">
          <div>
            <p className="eyebrow">本局状态</p>
            <h2>{session.level_title}</h2>
            <div className="result-meta-row">
              <span className="result-meta-chip">{session.chapter_title}</span>
              <span className="result-meta-chip">{formatLevelCode(session.chapter, session.level)}</span>
            </div>
          </div>
          <span className="tool-counter">{session.threat_label}</span>
        </div>

        <div className="live-score-strip">
          <div className="live-score-card">
            <span className="readout-label">当前分数</span>
            <strong className="live-score-value">{formatSignedScore(session.score)}</strong>
            <span className="live-score-meta">本关内实时累计</span>
          </div>

          <article className="result-card live-total-card">
            <span className="readout-label">累计分数</span>
            <strong className="live-total-value">
              {progression
                ? formatSignedScore(progression.campaign_total_score)
                : formatSignedScore(session.score)}
            </strong>
            <p>
              {progression
                ? `已完成 ${progression.completed_count}/${progression.total_levels} 关`
                : "当前账号 / 本地闯关总分"}
            </p>
          </article>
        </div>

        <div className="live-risk-grid">
          <article className="result-card live-metric-card">
            <span className="readout-label">稳定度</span>
            <strong>{session.stability}</strong>
          </article>
          <article className="result-card live-metric-card">
            <span className="readout-label">污染度</span>
            <strong>{session.corruption}</strong>
          </article>
        </div>

        <article className="result-card live-status-card">
          <span className="readout-label">当前任务</span>
          <strong>{session.mission_title}</strong>
          <p>{describeMissionFocus(session.mission_title)}</p>
        </article>

        <article className="result-card live-status-card">
          <span className="readout-label">剩余资源</span>
          <strong>
            {session.frames_remaining} 帧 / {session.remaining_guesses}/{session.max_guesses} 次猜测
          </strong>
          <p>{`卡牌 ${session.cards_remaining}/${session.max_cards}。现在只保留判断所需的最小读数。`}</p>
        </article>

        <div className="live-status-footer">
          <button className="secondary-button" onClick={onOpenHistory} type="button">
            历史记录 {historyCount > 0 ? `(${historyCount})` : ""}
          </button>
        </div>
      </section>
    );
  }

  return (
    <section className="panel result-panel">
      <div className="panel-heading result-panel__hero">
        <div>
          <p className="eyebrow">本局状态</p>
          <div className="result-title-stack">
            <span
              className={`result-state-chip ${
                session.status === "won"
                  ? "result-state-chip--won"
                  : "result-state-chip--lost"
              }`}
            >
              {session.status === "won" ? "通关成功" : "本关失败"}
            </span>
            <h2>{session.level_title}</h2>
          </div>
          <div className="result-meta-row">
            <span className="result-meta-chip">{session.chapter_title}</span>
            <span className="result-meta-chip">{formatLevelCode(session.chapter, session.level)}</span>
          </div>
        </div>
        <div className="score-total-block">
          <span className="readout-label">当前分数</span>
          <strong className="score-total-value">{formatSignedScore(session.score)}</strong>
        </div>
      </div>

      {session.status === "won" && session.awaiting_advancement ? (
        <section className="result-section">
          <div className="result-card result-card--action">
            <span className="readout-label">下一关已解锁</span>
            <strong>{session.next_level_title ?? "下一关"}</strong>
            <p>{session.next_level_summary ?? "难度将继续提升。"}</p>
            <div className="result-actions">
              <button
                className="action-button"
                disabled={busyAction !== null}
                onClick={onAdvance}
                type="button"
              >
                {busyAction === "advance" ? "载入下一关..." : "进入下一关"}
              </button>
              <button
                className="secondary-button"
                disabled={busyAction !== null}
                onClick={onRetryLevel}
                type="button"
              >
                重试本关
              </button>
            </div>
          </div>
        </section>
      ) : null}

      {session.status === "lost" ? (
        <section className="result-section">
          <div className="result-card result-card--action">
            <span className="readout-label">失败原因</span>
            <strong>{session.loss_reason ?? "本关失败"}</strong>
            <p>进度不会后退。整理判断后，直接重试当前关。</p>
            <div className="result-actions">
              <button
                className="action-button"
                disabled={busyAction !== null}
                onClick={onRetryLevel}
                type="button"
              >
                {busyAction === "start" ? "重载中..." : "重试本关"}
              </button>
            </div>
          </div>
        </section>
      ) : null}

      {session.campaign_complete ? (
        <section className="result-section">
          <div className="result-card result-card--action">
            <span className="readout-label">整套完成</span>
            <strong>12 关已全部归档</strong>
            <p>{session.next_level_summary ?? "你可以从第一关重新挑战整套档案。"}</p>
            <div className="result-actions">
              <button
                className="action-button"
                disabled={busyAction !== null}
                onClick={onRetryLevel}
                type="button"
              >
                {busyAction === "start" ? "重载中..." : "重新开始"}
              </button>
            </div>
          </div>
        </section>
      ) : null}

      <section className="result-section">
        <div className="result-section__header">
          <p className="eyebrow">闯关总分</p>
          <strong>
            {progression
              ? formatSignedScore(progression.campaign_total_score)
              : formatSignedScore(session.score)}
          </strong>
        </div>
        <div className="result-card result-card--summary">
          <span className="readout-label">本关最佳</span>
          <strong>
            {session.level_best_score !== null
              ? formatSignedScore(session.level_best_score)
              : "尚未记录"}
          </strong>
          <p>
            {session.level_best_improved
              ? "这局刷新了当前关卡的最佳分。"
              : "这局没有超过当前关卡的历史最佳。"}
          </p>
        </div>
      </section>

      <section className="result-section">
        <div className="result-section__header">
          <p className="eyebrow">最近分数变化</p>
          <strong>最近 5 条</strong>
        </div>
        <ScoreEventList
          emptyLabel="这局还没有触发任何分数变化。"
          events={session.score_events}
          limit={5}
        />
      </section>

      {breakdown ? (
        <section className="result-section">
          <div className="result-section__header">
            <p className="eyebrow">最终得分明细</p>
            <strong>总分 {formatSignedScore(breakdown.final_score)}</strong>
          </div>
          <ScoreBreakdownGrid
            items={summaryBreakdownItems(breakdown)}
            summary
          />

          <details className="result-disclosure">
            <summary>查看完整得分账单</summary>
            <ScoreBreakdownGrid items={breakdownItems(breakdown)} />
          </details>
        </section>
      ) : null}

      <section className="result-section">
        <div className="result-section__header">
          <p className="eyebrow">回看记录</p>
          <strong>最近 {historyCount} 局</strong>
        </div>
        <div className="result-actions">
          <button className="secondary-button" onClick={onOpenHistory} type="button">
            打开历史抽屉
          </button>
        </div>
      </section>
    </section>
  );
}
