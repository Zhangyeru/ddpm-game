import type { CardId, FreezeRegion } from "./types";

export const CARD_COPY: Record<
  CardId,
  { title: string; summary: string }
> = {
  "sharpen-outline": {
    title: "轮廓锐化",
    summary: "通用清晰度提升，适合前中期稳妥使用。"
  },
  "mechanical-lens": {
    title: "机械透镜",
    summary: "对机械体和建筑目标加成更强。"
  },
  "bio-scan": {
    title: "生物扫描",
    summary: "对生物类目标加成更强。"
  }
};

export const FREEZE_COPY: Record<
  FreezeRegion,
  { title: string; summary: string }
> = {
  "upper-left": {
    title: "左上区域",
    summary: "锁定画面的左上象限。"
  },
  center: {
    title: "中央区域",
    summary: "锁定最核心的主体轮廓。"
  },
  "lower-right": {
    title: "右下区域",
    summary: "锁定画面的右下象限。"
  }
};
