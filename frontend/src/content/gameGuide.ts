import type { CardId, SessionSnapshot } from "../game/types";

export type GuideCard = {
  title: string;
  detail: string;
  note: string;
};

export const RESOURCE_LIMITS = {
  guesses: 3,
  cards: 2
} as const;

export const SCORE_FORMULA_LABEL =
  "基础分 + 提前识别 + 剩余时间 + 稳定度 + 低污染 + 任务奖励 - 已用卡牌惩罚";

export const PLAY_RULES: readonly GuideCard[] = [
  {
    title: "先看清，再决定",
    detail: "图像会逐步显现，但每推进一步，稳定都会下降，污染都会上升。",
    note: "看出主体轮廓后再判断，别把提交当成试错。"
  },
  {
    title: "卡牌只在关键处用",
    detail: "每关可用卡牌有限。用对能稳住画面，用错会把线索带偏。",
    note: "先判断目标家族，再考虑要不要出高价值卡。"
  },
  {
    title: "猜错会立刻吃亏",
    detail: "每关可猜次数有限。猜错一次会掉分、掉稳定，还会提高污染。",
    note: "一次误判，往往会把后面的判断一并拖难。"
  },
  {
    title: "拖太久也会失败",
    detail: "帧数耗尽、稳定归零或污染爆表，都会立刻结束本局。",
    note: "等到完全看清，通常也已经错过高分窗口。"
  }
];

export const SCORE_RULES: readonly GuideCard[] = [
  {
    title: "越早锁定，收益越高",
    detail: "提前识别奖励和剩余时间奖励，都和剩余帧数直接相关。",
    note: "能确定时就提交，不要把高帧数等成低收益。"
  },
  {
    title: "局面越稳，分数越高",
    detail: "稳定度越高、污染越低，结算奖励就越完整。",
    note: "稳住局面，往往比盲目多看几步更值钱。"
  },
  {
    title: "出卡越多，扣分越多",
    detail: "每用一张卡，结算时都会扣掉一部分分数。",
    note: "卡牌不是越早越好，而是越准越值。"
  }
];

export const MISSION_GUIDES: readonly GuideCard[] = [
  {
    title: "快速识别",
    detail: "这局更奖励尽早提交。",
    note: "一旦答案够确定，就别继续白白消耗帧数。"
  },
  {
    title: "稳定回收",
    detail: "这局更看重稳定度和低污染。",
    note: "少犯错，比多拖几步更重要。"
  },
  {
    title: "少用卡牌",
    detail: "这局更奖励少用卡牌。",
    note: "能不用卡就别用，留到真正能锁答案的时候。"
  }
];

export const CARD_TOOL_GUIDE: Record<
  CardId,
  {
    title: string;
    effect: string;
    cost: string;
    timing: string;
  }
> = {
  "sharpen-outline": {
    title: "轮廓锐化",
    effect: "稳住轮廓：稳定 +5、污染 -4、得分 +8。",
    cost: "会计入卡牌扣分，但误用风险最低。",
    timing: "适合开局试探，或还没完全判断目标家族时。"
  },
  "mechanical-lens": {
    title: "机械透镜",
    effect: "命中机械/建筑时：稳定 +7、污染 -6、得分 +14。",
    cost: "用错会稳定 -5、污染 +8，并把线索引向误导分支。",
    timing: "看出车辆、器械或建筑轮廓后再用。"
  },
  "bio-scan": {
    title: "生物扫描",
    effect: "命中生物目标时：稳定 +7、污染 -6、得分 +14。",
    cost: "用错会稳定 -5、污染 +8，并明显提高误判风险。",
    timing: "看出耳朵、羽翼、肢体等生物特征后再用。"
  }
};

export function describeMissionFocus(missionTitle: string): string {
  if (missionTitle.includes("快速识别")) {
    return "这一局更奖励尽早提交。答案足够确定时，继续等待只会让收益缩水。";
  }
  if (missionTitle.includes("稳定回收")) {
    return "这一局更看重稳定和低污染。先避免误判，再考虑要不要多看几步。";
  }
  return "这一局更看重少用卡牌。能靠观察完成判断，就别为了求稳多出一张卡。";
}

export function summarizeToolPenalty(session: SessionSnapshot): string {
  const usedCards = session.max_cards - session.cards_remaining;
  return `已用卡牌 ${usedCards}/${session.max_cards}。卡用得越多，结算时扣得越多。`;
}

export function describeLivePriority(session: SessionSnapshot): string {
  if (session.remaining_guesses <= 1) {
    return "只剩最后机会，错误提交会同时打击分数、稳定度和污染线。";
  }
  if (session.corruption >= 70) {
    return "污染已经进入高压区，再拖延更可能看到错误轨迹，而不是更清晰的答案。";
  }
  if (session.frames_remaining <= Math.max(6, Math.floor(session.total_frames * 0.12))) {
    return "剩余帧已经不多，时间奖励正在快速见底，现在更该决定是否出手。";
  }
  return "当前还能靠剩余帧、稳定度和低污染继续抬分，但别把卡牌浪费在模糊判断上。";
}
