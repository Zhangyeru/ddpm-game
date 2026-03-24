import type { AuthUser, PendingActionKind, ProgressSnapshot } from "../game/types";
import { AuthPanel } from "./AuthPanel";
import {
  CARD_TOOL_GUIDE,
  MISSION_GUIDES,
  PLAY_RULES,
  SCORE_FORMULA_LABEL,
  SCORE_RULES
} from "../content/gameGuide";

const CARD_ORDER = ["sharpen-outline", "mechanical-lens", "bio-scan"] as const;
const CARD_FAMILY_LABEL: Record<(typeof CARD_ORDER)[number], string> = {
  "sharpen-outline": "通用稳像",
  "mechanical-lens": "机械 / 建筑",
  "bio-scan": "生物目标"
};
const QUICK_STEPS = [
  {
    title: "先看主体",
    detail: "先看轮廓和家族特征，不要把猜测当筛选器。"
  },
  {
    title: "再决定出卡",
    detail: "卡牌数量随关卡变化。命中能稳住画面，用错会把轨迹带偏。"
  },
  {
    title: "能确认就提交",
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
  progression: ProgressSnapshot | null;
  onStart: () => void;
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
  progression,
  onStart
}: LandingGuideProps) {
  const currentLevel = progression?.current_level ?? null;
  const actionLabel = busy
    ? "正在建立扫描轨道..."
    : progression?.campaign_complete
      ? "重开第一关"
      : progression?.completed_count
        ? "继续当前关"
        : "开始第一关";

  return (
    <section className="landing-console">
      <div className="landing-column landing-column--main">
        <section className="panel landing-panel landing-panel--hero">
          <p className="eyebrow">线性闯关</p>
          <h2>
            {currentLevel
              ? `${currentLevel.chapter_title} · 第 ${currentLevel.level} 关`
              : "观察图像，用对卡牌，在窗口关闭前完成识别"}
          </h2>
          <p>
            {currentLevel?.summary ??
              "目标会在去噪过程中逐渐显影。你要在稳定度被耗尽、污染度失控之前，用最少的卡牌判断答案并尽早提交。"}
          </p>

          <div className="hero-pill-row">
            <span className="hero-pill">
              {progression
                ? `已完成 ${progression.completed_count}/${progression.total_levels}`
                : "12 关线性推进"}
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
                  ? "整套档案已通关。你可以从第一关重新挑战，并继续刷新自己的最佳打法。"
                  : currentLevel
                    ? `当前任务：${currentLevel.mission_title}。`
                    : "猜得早、状态稳、污染低、少用卡，才是高分局。"}
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
        </section>

        <section className="panel landing-panel landing-panel--rules">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">规则与得分</p>
              <h2>完整说明</h2>
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
              <p className="eyebrow">卡牌工具</p>
              <h2>引导卡组</h2>
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
              <h2>先做这三步</h2>
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
            <div className="level-progress-grid">
              {progression.levels.map((level) => (
                <article
                  key={level.level_id}
                  className={`level-progress-card ${
                    level.is_current ? "level-progress-card--current" : ""
                  } ${level.is_completed ? "level-progress-card--completed" : ""}`}
                >
                  <strong>{`第 ${level.chapter}-${level.level} 关`}</strong>
                  <p>{level.level_title}</p>
                  <span>
                    {level.is_current
                      ? "当前关"
                      : level.is_completed
                        ? "已完成"
                        : level.is_unlocked
                          ? "已解锁"
                          : "未解锁"}
                  </span>
                </article>
              ))}
            </div>
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
