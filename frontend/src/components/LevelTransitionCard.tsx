import { useEffect, useState } from "react";
import type { LevelProgressItem } from "../game/types";

type LevelTransitionCardProps = {
  level: LevelProgressItem;
  onTransitionComplete: () => void;
};

export function LevelTransitionCard({
  level,
  onTransitionComplete
}: LevelTransitionCardProps) {
  const [isVisible, setIsVisible] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      setIsVisible(false);
      setTimeout(onTransitionComplete, 400);
    }, 2000);

    return () => clearTimeout(timer);
  }, [onTransitionComplete]);

  return (
    <div className={`level-transition-overlay ${isVisible ? "level-transition-overlay--visible" : ""}`}>
      <div className="level-transition-card">
        <div className="level-transition-header">
          <span className="level-transition-chapter">{level.chapter_title}</span>
          <span className="level-transition-divider">·</span>
          <span className="level-transition-level">关卡 {level.level}</span>
        </div>
        
        <h2 className="level-transition-title">{level.level_title}</h2>
        
        <div className="level-transition-details">
          <div className="level-transition-detail-row">
            <span className="level-transition-label">任务</span>
            <span className="level-transition-value">{level.mission_title.split("：")[0]}</span>
          </div>
          
          <div className="level-transition-detail-row">
            <span className="level-transition-label">难度</span>
            <span className="level-transition-value">{level.summary}</span>
          </div>
          
          <div className="level-transition-detail-row">
            <span className="level-transition-label">资源</span>
            <span className="level-transition-value">
              {level.max_guesses} 次猜测 · {level.max_cards} 张卡
            </span>
          </div>
        </div>
        
        <div className="level-transition-footer">
          <span className="level-transition-hint">准备开始...</span>
        </div>
      </div>
    </div>
  );
}
