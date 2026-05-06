import { memo, useCallback, useEffect, useRef, useState } from "react";
import type { SessionSnapshot } from "../game/types";
import { resolveApiUrl } from "../services/api";

type GameCanvasProps = {
  session: SessionSnapshot | null;
};

export const GameCanvas = memo(function GameCanvas({ session }: GameCanvasProps) {
  const revealMode = session?.status !== "playing";
  const progressPercent = session
    ? Math.round(session.progress * 100)
    : 0;
  const stabilityPercent = session
    ? Math.max(0, Math.min(100, session.stability))
    : 0;
  const corruptionPercent = session
    ? Math.max(0, Math.min(100, session.corruption))
    : 0;
  const [imageError, setImageError] = useState(false);
  const preloadedRef = useRef<Set<string>>(new Set());

  const imageUrl = session ? resolveApiUrl(session.image_url) : null;

  useEffect(() => {
    setImageError(false);
  }, [imageUrl]);

  useEffect(() => {
    if (!session || revealMode) return;

    const nextFrame = session.frame_index + 1;
    if (nextFrame >= session.total_frames) return;

    const nextUrl = imageUrl?.replace(
      /frame_\d+/,
      `frame_${String(nextFrame).padStart(4, "0")}`
    );
    if (!nextUrl || preloadedRef.current.has(nextUrl)) return;

    preloadedRef.current.add(nextUrl);
    const img = new Image();
    img.src = nextUrl;
  }, [session?.frame_index, session?.total_frames, imageUrl, revealMode, session]);

  const handleImageError = useCallback(() => {
    setImageError(true);
  }, []);

  return (
    <section className="panel canvas-panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">{revealMode ? "结果画面" : "解码视图"}</p>
          <h2>{revealMode ? "答案揭示" : "主画布"}</h2>
        </div>
        {session ? (
          <div className="canvas-meta-group">
            <p className="canvas-meta">
              {revealMode
                ? `已揭示目标：${session.revealed_target ?? "未知目标"}`
                : `帧 ${session.frame_index + 1}/${session.total_frames}`}
            </p>
          </div>
        ) : null}
      </div>

      <div className="screen-frame">
        {session && imageUrl && !imageError ? (
          <>
            <img
              className="screen-image"
              src={imageUrl}
              alt={revealMode ? "正确答案图像" : "去噪过程画面"}
              onError={handleImageError}
            />
            {!revealMode ? <div className="screen-overlay" /> : null}
          </>
        ) : session && imageError ? (
          <div className="screen-placeholder">
            <p>图像加载失败。</p>
            <span>请检查网络连接后重试本关。</span>
          </div>
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
    </section>
  );
});
