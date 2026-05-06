import { useEffect, useState } from "react";
import type { SessionSnapshot } from "../game/types";

const TRANSITION_VISIBLE_MS = 2000;
const TRANSITION_FADE_MS = 400;
const COUNTDOWN_INTERVAL_MS = 100;

type LevelTransitionCardProps = {
  session: Pick<
    SessionSnapshot,
    | "chapter_title"
    | "level"
    | "level_title"
    | "level_summary"
    | "mission_title"
    | "max_guesses"
    | "max_cards"
  >;
  onTransitionComplete: () => void;
};

export function LevelTransitionCard({
  session,
  onTransitionComplete
}: LevelTransitionCardProps) {
  const [isVisible, setIsVisible] = useState(true);
  const [remainingMs, setRemainingMs] = useState(TRANSITION_VISIBLE_MS);
  const remainingSeconds = Math.max(0, Math.ceil(remainingMs / 1000));
  const progress = Math.max(
    0,
    Math.min(1, remainingMs / TRANSITION_VISIBLE_MS)
  );

  useEffect(() => {
    let completeTimer: number | undefined;
    const startedAt = window.performance.now();
    const countdownTimer = window.setInterval(() => {
      const elapsedMs = window.performance.now() - startedAt;
      setRemainingMs(Math.max(0, TRANSITION_VISIBLE_MS - elapsedMs));
    }, COUNTDOWN_INTERVAL_MS);
    const timer = setTimeout(() => {
      setIsVisible(false);
      setRemainingMs(0);
      completeTimer = window.setTimeout(onTransitionComplete, TRANSITION_FADE_MS);
    }, TRANSITION_VISIBLE_MS);

    return () => {
      window.clearInterval(countdownTimer);
      window.clearTimeout(timer);
      if (completeTimer !== undefined) {
        window.clearTimeout(completeTimer);
      }
    };
  }, [onTransitionComplete]);

  return (
    <div className={`level-transition-overlay ${isVisible ? "level-transition-overlay--visible" : ""}`}>
      <div className="level-transition-card">
        <div className="level-transition-header">
          <span className="level-transition-chapter">{session.chapter_title}</span>
          <span className="level-transition-divider">·</span>
          <span className="level-transition-level">关卡 {session.level}</span>
        </div>

        <h2 className="level-transition-title">{session.level_title}</h2>

        <div className="level-transition-details">
          <div className="level-transition-detail-row">
            <span className="level-transition-label">任务</span>
            <span className="level-transition-value">{session.mission_title.split("：")[0]}</span>
          </div>

          <div className="level-transition-detail-row">
            <span className="level-transition-label">难度</span>
            <span className="level-transition-value">{session.level_summary}</span>
          </div>

          <div className="level-transition-detail-row">
            <span className="level-transition-label">资源</span>
            <span className="level-transition-value">
              {session.max_guesses} 次猜测 · {session.max_cards} 张卡
            </span>
          </div>
        </div>

        <div className="level-transition-footer">
          <span className="level-transition-hint">
            {remainingSeconds} 秒后自动进入关卡
          </span>
          <div
            aria-hidden="true"
            className="level-transition-progress"
          >
            <span
              className="level-transition-progress__bar"
              style={{ transform: `scaleX(${progress})` }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
