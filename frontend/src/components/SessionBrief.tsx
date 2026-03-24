import {
  describeLivePriority,
  describeMissionFocus
} from "../content/gameGuide";
import type { SessionSnapshot } from "../game/types";

type SessionBriefProps = {
  session: SessionSnapshot;
};

export function SessionBrief({ session }: SessionBriefProps) {
  return (
    <section className="panel side-panel session-brief">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">局势摘要</p>
          <h2>当前重点</h2>
        </div>
        <span className="tool-counter">{session.threat_label}</span>
      </div>

      <div className="brief-grid">
        <article className="brief-card">
          <span className="readout-label">当前任务</span>
          <strong>{session.mission_title}</strong>
          <p>{describeMissionFocus(session.mission_title)}</p>
        </article>

        <article className="brief-card">
          <span className="readout-label">现场判断</span>
          <strong>{session.phase_label}</strong>
          <p>{describeLivePriority(session)}</p>
        </article>

        <article className="brief-card">
          <span className="readout-label">资源窗口</span>
          <strong>
            {session.frames_remaining} 帧 / {session.remaining_guesses} 次猜测 /{" "}
            {session.cards_remaining} 张卡
          </strong>
          <p>右栏只保留操作优先视图，分数账单和历史在结算后再展开。</p>
        </article>
      </div>
    </section>
  );
}
