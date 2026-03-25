import { useEffect, useState } from "react";
import type {
  AuthUser,
  PendingActionKind,
  ProgressSnapshot
} from "../game/types";
import { AuthPanel } from "./AuthPanel";
import { formatLevelCode } from "../game/levelPresentation";
import { formatSignedScore } from "../game/scorePresentation";
import {
  CARD_TOOL_GUIDE,
  MISSION_GUIDES,
  PLAY_RULES,
  SCORE_FORMULA_LABEL,
  SCORE_RULES
} from "../content/gameGuide";

const CARD_ORDER = ["sharpen-outline", "mechanical-lens", "bio-scan"] as const;
const CARD_FAMILY_LABEL: Record<(typeof CARD_ORDER)[number], string> = {
  "sharpen-outline": "通用",
  "mechanical-lens": "机械 / 建筑",
  "bio-scan": "生物"
};
const QUICK_STEPS = [
  {
    title: "先看清主体",
    detail: "先看轮廓和家族特征，不要把提交当成筛选器。"
  },
  {
    title: "再决定出卡",
    detail: "卡牌数量会随关卡变化。命中能稳住画面，用错会把线索带偏。"
  },
  {
    title: "能确定就提交",
    detail: "继续等待会吃掉时间奖励，也可能把污染拖高。"
  }
] as const;

type LandingGuideProps = {
  authBusyAction: Extract<PendingActionKind, "login" | "logout" | "register"> | null;
  authError: string | null;
  authUser: AuthUser | null;
  busy?: boolean;
  onClearAuthError: () => void;
  onLogin: (username: string, password: string) => Promise<void>;
  onLogout: () => Promise<void>;
  onRegister: (username: string, password: string) => Promise<void>;
  onOpenLeaderboard: () => void;
  progression: ProgressSnapshot | null;
  onStart: () => void;
  onStartLevel: (levelId: string) => void;
};

export function LandingGuide({
  authBusyAction,
  authError,
  authUser,
  busy = false,
  onClearAuthError,
  onLogin,
  onLogout,
  onRegister,
  onOpenLeaderboard,
  progression,
  onStart,
  onStartLevel
}: LandingGuideProps) {
  const currentLevel = progression?.current_level ?? null;
  const groupedLevels = progression
    ? progression.levels.reduce<Array<{
        chapter: number;
        chapterTitle: string;
        levels: ProgressSnapshot["levels"];
      }>>((groups, level) => {
        const currentGroup = groups[groups.length - 1];
        if (!currentGroup || currentGroup.chapter !== level.chapter) {
          groups.push({
            chapter: level.chapter,
            chapterTitle: level.chapter_title,
            levels: [level]
          });
          return groups;
        }

        currentGroup.levels.push(level);
        return groups;
      }, [])
    : [];
  const [expandedChapters, setExpandedChapters] = useState<Record<number, boolean>>({});
  const actionLabel = busy
    ? "正在建立扫描轨道..."
    : progression?.campaign_complete
      ? "重开第一关"
      : progression?.completed_count
        ? "继续当前关"
        : "开始第一关";

  useEffect(() => {
    if (!groupedLevels.length) {
      return;
    }

    setExpandedChapters((current) => {
      const next = { ...current };
      const targetChapter = currentLevel?.chapter ?? groupedLevels[0].chapter;
      if (!(targetChapter in next)) {
        next[targetChapter] = true;
      }
      return next;
    });
  }, [currentLevel?.chapter, groupedLevels]);

  function toggleChapter(chapter: number) {
    setExpandedChapters((current) => ({
      ...current,
      [chapter]: !current[chapter]
    }));
  }

  return (
    <section className="landing-console">
      <div className="landing-column landing-column--main">
        <section className="panel landing-panel landing-panel--hero">
          <p className="eyebrow">逐关推进</p>
          <h2>
            {currentLevel
              ? `${currentLevel.chapter_title} · ${formatLevelCode(currentLevel.chapter, currentLevel.level)}`
              : "看清目标、用好卡牌，在窗口关闭前完成判定"}
          </h2>
          <p>
            {currentLevel?.summary ??
              "目标会在去噪过程中逐步显现。你要在稳定度被耗尽、污染失控之前，用尽量少的卡牌锁定答案。"}
          </p>

          <div className="hero-pill-row">
            <span className="hero-pill">
              {progression
                ? `已完成 ${progression.completed_count}/${progression.total_levels}`
                : "12 关逐步推进"}
            </span>
            <span className="hero-pill">
              {progression
                ? `闯关总分 ${formatSignedScore(progression.campaign_total_score)}`
                : "每关只记录最高分"}
            </span>
            <span className="hero-pill">
              {currentLevel ? `${currentLevel.candidate_count} 项候选` : "候选数量逐关提升"}
            </span>
            <span className="hero-pill">
              {currentLevel ? `${currentLevel.max_guesses} 次猜测` : "猜测次数由关卡决定"}
            </span>
            <span className="hero-pill">
              {currentLevel ? `${currentLevel.max_cards} 张引导卡` : "卡牌数量由关卡决定"}
            </span>
          </div>

          <div className="landing-hero-footer">
            <div className="landing-note">
              <span className="readout-label">得分公式速览</span>
              <strong>{SCORE_FORMULA_LABEL}</strong>
              <p>
                {progression?.campaign_complete
                  ? "整套档案已经走通。你可以从第一关重新挑战，继续刷新自己的最好成绩。"
                  : currentLevel
                    ? `本关目标：${currentLevel.mission_title}。`
                    : "猜得早、局面稳、污染低、少出卡，才是高分局。"}
              </p>
            </div>

            <button
              className="action-button landing-primary-action"
              disabled={busy}
              onClick={onStart}
              type="button"
            >
              {actionLabel}
            </button>
          </div>
          <div className="landing-secondary-actions">
            <button className="secondary-button" onClick={onOpenLeaderboard} type="button">
              查看总分排行
            </button>
          </div>
        </section>

        <section className="panel landing-panel landing-panel--rules">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">玩法说明</p>
              <h2>进入前先看</h2>
            </div>
            {currentLevel ? (
              <span className="tool-counter">{currentLevel.mission_title}</span>
            ) : null}
          </div>

          <div className="landing-rule-columns">
            <div className="landing-rule-group">
              <p className="section-label">核心规则</p>
              <div className="landing-stack">
                {PLAY_RULES.map((rule) => (
                  <article
                    key={rule.title}
                    className="landing-card"
                  >
                    <strong>{rule.title}</strong>
                    <p>{rule.detail}</p>
                    <span>{rule.note}</span>
                  </article>
                ))}
              </div>
            </div>

            <div className="landing-rule-group">
              <p className="section-label">得分规则</p>
              <div className="landing-stack">
                {SCORE_RULES.map((rule) => (
                  <article
                    key={rule.title}
                    className="landing-card"
                  >
                    <strong>{rule.title}</strong>
                    <p>{rule.detail}</p>
                    <span>{rule.note}</span>
                  </article>
                ))}
              </div>
            </div>
          </div>
        </section>

        <section className="panel landing-panel landing-panel--cards">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">可用卡牌</p>
              <h2>卡牌说明</h2>
            </div>
            <span className="tool-counter">
              {currentLevel ? `${currentLevel.max_cards} 张可用` : "按关卡发放"}
            </span>
          </div>

          <p className="landing-tool-intro">
            先看主体家族，再决定是否出卡。通用卡更稳，专用卡收益更高，但用错会把轨迹带偏。
          </p>

          <div className="landing-tool-grid">
            {CARD_ORDER.map((cardId) => {
              const guide = CARD_TOOL_GUIDE[cardId];

              return (
                <article
                  key={cardId}
                  className="landing-card landing-card--tool"
                >
                  <div className="landing-tool-card__header">
                    <strong>{guide.title}</strong>
                    <span className="landing-tool-card__badge">
                      {CARD_FAMILY_LABEL[cardId]}
                    </span>
                  </div>
                  <div className="landing-tool-card__body">
                    <p>
                      <span className="guide-card__label">效果</span>
                      {guide.effect}
                    </p>
                    <p>
                      <span className="guide-card__label">代价</span>
                      {guide.cost}
                    </p>
                    <p>
                      <span className="guide-card__label">适合</span>
                      {guide.timing}
                    </p>
                  </div>
                </article>
              );
            })}
          </div>
        </section>
      </div>

      <div className="landing-column landing-column--side">
        <AuthPanel
          authBusyAction={authBusyAction}
          authError={authError}
          authUser={authUser}
          onClearError={onClearAuthError}
          onLogin={onLogin}
          onLogout={onLogout}
          onRegister={onRegister}
          progression={progression}
        />

        <section className="panel landing-panel landing-panel--summary">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">闯关进度</p>
              <h2>开局三步</h2>
            </div>
            {progression ? (
              <span className="tool-counter">
                {progression.completed_count}/{progression.total_levels}
              </span>
            ) : null}
          </div>

          <div className="landing-stack">
            {QUICK_STEPS.map((step, index) => (
              <article
                key={step.title}
                className="landing-card"
              >
                <strong>{`${index + 1}. ${step.title}`}</strong>
                <p>{step.detail}</p>
              </article>
            ))}
          </div>

          {progression ? (
            <>
              <div className="level-progress-header">
                <span className="readout-label">关卡列表</span>
                <p>点击任意关卡卡片，直接进入对应关卡。</p>
              </div>

              <div className="level-progress-chapters">
                {groupedLevels.map((group) => (
                  <section className="level-progress-chapter" key={group.chapter}>
                    <div
                      className={`level-progress-chapter__header ${
                        group.chapter === currentLevel?.chapter
                          ? "level-progress-chapter__header--current"
                          : ""
                      }`}
                    >
                      <div className="level-progress-chapter__copy">
                        <span className="readout-label">{`第 ${group.chapter} 章`}</span>
                        <strong>{group.chapterTitle}</strong>
                        <p>
                          {`已完成 ${
                            group.levels.filter((level) => level.is_completed).length
                          }/${group.levels.length} 关${
                            group.chapter === currentLevel?.chapter ? " · 当前章节" : ""
                          }`}
                        </p>
                      </div>
                      <button
                        className="secondary-button level-progress-chapter__toggle"
                        onClick={() => toggleChapter(group.chapter)}
                        type="button"
                      >
                        {expandedChapters[group.chapter] ? "收起本章" : "展开本章"}
                      </button>
                    </div>

                    {expandedChapters[group.chapter] ? (
                      <div className="level-progress-grid">
                        {group.levels.map((level) => (
                          <button
                            key={level.level_id}
                            type="button"
                            onClick={() => onStartLevel(level.level_id)}
                            className={`level-progress-card ${
                              level.is_current ? "level-progress-card--current" : ""
                            } ${level.is_completed ? "level-progress-card--completed" : ""} ${
                              busy ? "level-progress-card--busy" : ""
                            }`}
                            disabled={busy}
                          >
                            {level.is_current ? (
                              <span className="level-progress-card__marker">当前选择</span>
                            ) : null}
                            <strong>{formatLevelCode(level.chapter, level.level)}</strong>
                            <p>{level.level_title}</p>
                            <div className="level-progress-card__chips">
                              <span className="level-progress-card__chip">
                                {level.mission_title.split("：")[0]}
                              </span>
                              <span className="level-progress-card__chip">
                                {`${level.max_guesses} 次猜测`}
                              </span>
                              <span className="level-progress-card__chip">
                                {`${level.max_cards} 张卡`}
                              </span>
                            </div>
                            <span className="level-progress-card__summary">{level.summary}</span>
                            {level.best_score !== null ? (
                              <span className="level-progress-score">
                                {`最佳分 ${formatSignedScore(level.best_score)}`}
                              </span>
                            ) : (
                              <span className="level-progress-score level-progress-score--muted">
                                尚无记录
                              </span>
                            )}
                            <div className="level-progress-card__footer">
                              <span>
                                {level.is_current
                                  ? "当前关"
                                  : level.is_completed
                                    ? "已完成"
                                    : level.is_unlocked
                                      ? "已解锁"
                                      : "未解锁"}
                              </span>
                              <span className="level-progress-card__action">
                                {busy
                                  ? "载入中..."
                                  : level.is_current
                                    ? "继续此关"
                                    : level.is_completed
                                      ? "重新挑战"
                                      : "点击进入"}
                              </span>
                            </div>
                          </button>
                        ))}
                      </div>
                    ) : null}
                  </section>
                ))}
              </div>
            </>
          ) : (
            <div className="landing-mini-grid">
              {MISSION_GUIDES.map((mission) => (
                <article
                  key={mission.title}
                  className="mission-card"
                >
                  <strong>{mission.title}</strong>
                  <p>{mission.detail}</p>
                  <span>{mission.note}</span>
                </article>
              ))}
            </div>
          )}
        </section>

      </div>
    </section>
  );
}
