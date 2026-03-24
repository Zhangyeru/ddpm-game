import {
  CARD_TOOL_GUIDE,
  MISSION_GUIDES,
  PLAY_RULES,
  RESOURCE_LIMITS,
  SCORE_FORMULA_LABEL,
  SCORE_RULES
} from "../content/gameGuide";

const CARD_ORDER = ["sharpen-outline", "mechanical-lens", "bio-scan"] as const;
const QUICK_STEPS = [
  {
    title: "先看主体",
    detail: "先看轮廓和家族特征，不要把猜测当筛选器。"
  },
  {
    title: "再决定出卡",
    detail: "只有两张卡。命中能稳住画面，用错会把轨迹带偏。"
  },
  {
    title: "能确认就提交",
    detail: "继续等待会吃掉时间奖励，也可能把污染拖高。"
  }
] as const;

type LandingGuideProps = {
  busy?: boolean;
  onStart: () => void;
};

export function LandingGuide({ busy = false, onStart }: LandingGuideProps) {
  return (
    <section className="landing-console">
      <div className="landing-column landing-column--main">
        <section className="panel landing-panel landing-panel--hero">
          <p className="eyebrow">完整规则页</p>
          <h2>观察图像，用对卡牌，在窗口关闭前完成识别</h2>
          <p>
            目标会在去噪过程中逐渐显影。你要在稳定度被耗尽、污染度失控之前，
            用最少的卡牌判断答案并尽早提交。
          </p>

          <div className="hero-pill-row">
            <span className="hero-pill">{RESOURCE_LIMITS.guesses} 次猜测</span>
            <span className="hero-pill">{RESOURCE_LIMITS.cards} 张引导卡</span>
            <span className="hero-pill">100 步去噪</span>
          </div>

          <div className="landing-hero-footer">
            <div className="landing-note">
              <span className="readout-label">得分公式速览</span>
              <strong>{SCORE_FORMULA_LABEL}</strong>
              <p>猜得早、状态稳、污染低、少用卡，才是高分局。</p>
            </div>

            <button
              className="action-button landing-primary-action"
              disabled={busy}
              onClick={onStart}
              type="button"
            >
              {busy ? "正在建立扫描轨道..." : "开始首局扫描"}
            </button>
          </div>
        </section>

        <section className="panel landing-panel landing-panel--rules">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">规则与得分</p>
              <h2>完整说明</h2>
            </div>
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
      </div>

      <div className="landing-column landing-column--side">
        <section className="panel landing-panel landing-panel--summary">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">一局怎么打</p>
              <h2>先做这三步</h2>
            </div>
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
        </section>

        <section className="panel landing-panel landing-panel--cards">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">卡牌工具</p>
              <h2>引导卡组</h2>
            </div>
          </div>

          <div className="landing-stack">
            {CARD_ORDER.map((cardId) => {
              const guide = CARD_TOOL_GUIDE[cardId];

              return (
                <article
                  key={cardId}
                  className="landing-card landing-card--tool"
                >
                  <strong>{guide.title}</strong>
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
                </article>
              );
            })}
          </div>
        </section>
      </div>
    </section>
  );
}
