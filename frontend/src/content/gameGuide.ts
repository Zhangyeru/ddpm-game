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
    title: "先看，不要乱猜",
    detail: "图像会越来越清楚，但每一步都会掉稳定、涨污染。",
    note: "看懂主体轮廓再出手，别把猜测当试错按钮。"
  },
  {
    title: "卡牌是唯一主动工具",
    detail: "卡牌数量由关卡决定。用对能稳住画面，用错会把轨迹带偏。",
    note: "先判断目标家族，再决定是否出高价值卡。"
  },
  {
    title: "猜错代价直接生效",
    detail: "猜测次数由关卡决定。猜错一次会 -18 分、稳定 -12、污染 +14。",
    note: "错误提交既丢分，也会让后面的画面更难判断。"
  },
  {
    title: "拖太久同样会输",
    detail: "帧耗尽、稳定归零或污染爆表，都会立即结束本局。",
    note: "等到完全清楚通常不是高分打法。"
  }
];

export const SCORE_RULES: readonly GuideCard[] = [
  {
    title: "越早识别越高分",
    detail: "提前识别奖励和剩余时间奖励都跟剩余帧直接相关。",
    note: "能确定时就出手，不要把高帧数等成低收益。"
  },
  {
    title: "稳和净都会加分",
    detail: "稳定度越高，奖励越高；污染越低，低污染奖励越高。",
    note: "稳住局面，比盲目拖延更值钱。"
  },
  {
    title: "卡牌会吃结算惩罚",
    detail: "每用一张卡，最终分都会被扣掉一部分。",
    note: "卡牌不是越早越好，而是越准越值。"
  }
];

export const MISSION_GUIDES: readonly GuideCard[] = [
  {
    title: "速判回收",
    detail: "这局更奖励尽早提交。",
    note: "一旦答案够确定，就别继续白白消耗帧数。"
  },
  {
    title: "稳态回收",
    detail: "这局更看重稳定度和低污染。",
    note: "少犯错，比多拖几步更重要。"
  },
  {
    title: "低干预回收",
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
    effect: "通用增强：稳定 +5、污染 -4、得分 +8。",
    cost: "会计入卡牌惩罚，但风险最低。",
    timing: "开局试探，或还没完全确认目标家族时。"
  },
  "mechanical-lens": {
    title: "机械透镜",
    effect: "命中机械/建筑：稳定 +7、污染 -6、得分 +14。",
    cost: "用错会稳定 -5、污染 +8，并推向误导轨迹。",
    timing: "看出车辆、结构体或金属轮廓后再用。"
  },
  "bio-scan": {
    title: "生物扫描",
    effect: "命中生物：稳定 +7、污染 -6、得分 +14。",
    cost: "用错会稳定 -5、污染 +8，并提高误判风险。",
    timing: "看出耳朵、羽翼、肢体等生物轮廓后再用。"
  }
};

export function describeMissionFocus(missionTitle: string): string {
  if (missionTitle.includes("速判回收")) {
    return "这局看重尽早提交。答案足够确定时，继续等只会让奖励缩水。";
  }
  if (missionTitle.includes("稳态回收")) {
    return "这局看重稳定和低污染。先避免误判，再考虑多看几步。";
  }
  return "这局看重少用卡牌。能靠观察完成判断，就别为了求稳而多出一张卡。";
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
    return "剩余帧已经不多，时间奖励正在快速见底，现在更应该判断是否出手。";
  }
  return "当前还能靠剩余帧、稳定度和低污染继续抬分，但别把卡牌浪费在模糊判断上。";
}
