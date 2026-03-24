import {
  SCORE_FORMULA_LABEL,
  describeLivePriority,
  describeMissionFocus,
  summarizeToolPenalty
} from "../content/gameGuide";
import { ScoreBreakdownGrid } from "./ScoreBreakdownGrid";
import { ScoreEventList } from "./ScoreEventList";
import {
  summaryBreakdownItems,
  formatSignedScore,
  breakdownItems
} from "../game/scorePresentation";
import type { SessionSnapshot } from "../game/types";

type ScorePanelProps = {
  historyCount: number;
  onOpenHistory: () => void;
  session: SessionSnapshot;
};

export function ScorePanel({
  historyCount,
  onOpenHistory,
  session
}: ScorePanelProps) {
  const focus = describeMissionFocus(session.mission_title);
  const livePriority = describeLivePriority(session);
  const breakdown = session.score_breakdown;
  const isFinished = session.status !== "playing";
  const latestEvents = isFinished ? 5 : 3;

  return (
    <section className="panel result-panel">
      <div className="panel-heading result-panel__hero">
        <div>
          <p className="eyebrow">本局状态</p>
          <h2>
            {session.status === "playing"
              ? `${session.phase_label}：判断时机比等待更重要`
              : session.status === "won"
                ? `识别成功：${session.revealed_target}`
                : `识别失败：${session.revealed_target}`}
          </h2>
        </div>
        <div className="score-total-block">
          <span className="readout-label">当前分数</span>
          <strong className="score-total-value">{formatSignedScore(session.score)}</strong>
        </div>
      </div>

      <div className="result-grid result-grid--compact">
        <article className="result-card">
          <span className="readout-label">任务重点</span>
          <strong>{focus}</strong>
        </article>
        <article className="result-card">
          <span className="readout-label">当前局势</span>
          <strong>{livePriority}</strong>
        </article>
        <article className="result-card">
          <span className="readout-label">卡牌成本</span>
          <strong>{summarizeToolPenalty(session)}</strong>
        </article>
        <article className="result-card">
          <span className="readout-label">得分公式</span>
          <strong>{SCORE_FORMULA_LABEL}</strong>
        </article>
      </div>

      <section className="result-section">
        <div className="result-section__header">
          <p className="eyebrow">最近分数变化</p>
          <strong>{isFinished ? `最近 ${latestEvents} 条` : "只看关键变化"}</strong>
        </div>
        <ScoreEventList
          emptyLabel="这局还没有触发任何分数变化。"
          events={session.score_events}
          limit={latestEvents}
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

          {isFinished ? (
            <details className="result-disclosure">
              <summary>查看完整得分账单</summary>
              <ScoreBreakdownGrid items={breakdownItems(breakdown)} />
            </details>
          ) : null}

          {session.loss_reason ? (
            <p className="result-note">失败原因：{session.loss_reason}</p>
          ) : null}
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
          <span className="result-note">
            支持搜索目标、筛选胜负，并按时间或分数排序。
          </span>
        </div>
      </section>

      <p className="result-note">
        猜错会 -18 分并抬高风险；猜测用尽、稳定归零、污染爆表或帧耗尽都会直接结束本局。
      </p>
    </section>
  );
}
