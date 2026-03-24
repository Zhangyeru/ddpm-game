import type { SessionSnapshot } from "../game/types";
import { resolveApiUrl } from "../services/api";

type GameCanvasProps = {
  session: SessionSnapshot | null;
};

export function GameCanvas({ session }: GameCanvasProps) {
  const progressPercent = session
    ? Math.round(session.progress * 100)
    : 0;
  const stabilityPercent = session
    ? Math.max(0, Math.min(100, session.stability))
    : 0;
  const corruptionPercent = session
    ? Math.max(0, Math.min(100, session.corruption))
    : 0;

  return (
    <section className="panel canvas-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">解码视图</p>
          <h2>主画布</h2>
        </div>
        {session ? (
          <div className="canvas-meta-group">
            <p className="canvas-meta">
              帧 {session.frame_index + 1}/{session.total_frames}
            </p>
            <p className="canvas-meta">{session.phase_label}</p>
          </div>
        ) : null}
      </div>

      <div className="screen-frame">
        {session ? (
          <>
            <img
              className="screen-image"
              src={resolveApiUrl(session.image_url)}
              alt="去噪过程画面"
            />
            <div className="screen-overlay" />
          </>
        ) : (
          <div className="screen-placeholder">
            <p>当前没有进行中的扫描。</p>
            <span>启动扫描后，系统会渲染第一条去噪轨迹。</span>
          </div>
        )}
      </div>

      <div className="progress-strip">
        <div
          className="progress-fill"
          style={{ width: `${progressPercent}%` }}
        />
      </div>

      <div className="meter-stack">
        <div className="meter-card">
          <div className="meter-label-row">
            <span className="readout-label">稳定度</span>
            <strong>{session ? session.stability : "--"}</strong>
          </div>
          <div className="meter-bar">
            <div
              className="meter-fill meter-fill--stability"
              style={{ width: `${stabilityPercent}%` }}
            />
          </div>
        </div>
        <div className="meter-card">
          <div className="meter-label-row">
            <span className="readout-label">污染度</span>
            <strong>{session ? session.threat_label : "--"}</strong>
          </div>
          <div className="meter-bar">
            <div
              className="meter-fill meter-fill--corruption"
              style={{ width: `${corruptionPercent}%` }}
            />
          </div>
        </div>
      </div>

      <div className="canvas-readout">
        <div>
          <span className="readout-label">提示谱带</span>
          <strong>{session?.hint ?? "等待锁定目标。"}</strong>
        </div>
        <div>
          <span className="readout-label">风险等级</span>
          <strong>
            {session ? session.threat_label : "--"}
          </strong>
        </div>
        <div>
          <span className="readout-label">当前任务</span>
          <strong>
            {session?.mission_title ?? "等待任务分配"}
          </strong>
        </div>
        <div>
          <span className="readout-label">资源摘要</span>
          <strong>
            {session
              ? `剩余 ${session.frames_remaining} 帧 / 猜测 ${session.remaining_guesses} / 卡牌 ${session.cards_remaining}`
              : "--"}
          </strong>
        </div>
      </div>
    </section>
  );
}
