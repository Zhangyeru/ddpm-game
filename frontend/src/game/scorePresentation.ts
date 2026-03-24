import type { ScoreBreakdown } from "./types";

export type ScoreBreakdownItem = {
  label: string;
  value: number;
};

export function formatSignedScore(value: number): string {
  if (value > 0) {
    return `+${value}`;
  }

  return `${value}`;
}

export function formatEndedAt(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString("zh-CN", {
    hour12: false,
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit"
  });
}

export function breakdownItems(
  breakdown: ScoreBreakdown
): ScoreBreakdownItem[] {
  return [
    { label: "过程分", value: breakdown.process_score_total },
    { label: "基础分", value: breakdown.base_score },
    { label: "提前识别", value: breakdown.early_bonus },
    { label: "剩余时间", value: breakdown.time_bonus },
    { label: "稳定奖励", value: breakdown.stability_bonus },
    { label: "低污染奖励", value: breakdown.low_corruption_bonus },
    { label: "任务奖励", value: breakdown.mission_bonus },
    { label: "卡牌惩罚", value: -breakdown.card_penalty },
    { label: "结算合计", value: breakdown.settlement_score },
    { label: "最终得分", value: breakdown.final_score }
  ];
}

export function summaryBreakdownItems(
  breakdown: ScoreBreakdown
): ScoreBreakdownItem[] {
  return [
    { label: "过程分", value: breakdown.process_score_total },
    { label: "结算合计", value: breakdown.settlement_score },
    { label: "卡牌惩罚", value: -breakdown.card_penalty },
    { label: "最终得分", value: breakdown.final_score }
  ];
}
