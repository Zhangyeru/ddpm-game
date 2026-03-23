import type { SessionSnapshot } from "../game/types";

type GameCanvasProps = {
  session: SessionSnapshot | null;
};

export function GameCanvas({ session }: GameCanvasProps) {
  const progressPercent = session
    ? Math.round(session.progress * 100)
    : 0;

  return (
    <section className="panel canvas-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">解码视图</p>
          <h2>主画布</h2>
        </div>
        {session ? (
          <p className="canvas-meta">
            帧 {session.frame_index + 1}/{session.total_frames}
          </p>
        ) : null}
      </div>

      <div className="screen-frame">
        {session ? (
          <>
            <img
              className="screen-image"
              src={session.image_data}
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

      <div className="canvas-readout">
        <div>
          <span className="readout-label">提示谱带</span>
          <strong>{session?.hint ?? "等待锁定目标。"}</strong>
        </div>
        <div>
          <span className="readout-label">剩余猜测</span>
          <strong>
            {session ? session.remaining_guesses : "--"}
          </strong>
        </div>
        <div>
          <span className="readout-label">剩余卡牌</span>
          <strong>
            {session ? session.cards_remaining : "--"}
          </strong>
        </div>
      </div>
    </section>
  );
}
