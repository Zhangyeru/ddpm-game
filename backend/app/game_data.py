from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CardDefinition:
    title: str
    summary: str
    bonus_family: str | None
    clarity_bonus: float


@dataclass(frozen=True)
class TargetDefinition:
    label: str
    family: str
    hint: str
    accent: str


CARD_DEFINITIONS: dict[str, CardDefinition] = {
    "sharpen-outline": CardDefinition(
        title="轮廓锐化",
        summary="提供通用轮廓增强。",
        bonus_family=None,
        clarity_bonus=0.12,
    ),
    "mechanical-lens": CardDefinition(
        title="机械透镜",
        summary="对机械体和建筑目标效果更强。",
        bonus_family="machine",
        clarity_bonus=0.07,
    ),
    "bio-scan": CardDefinition(
        title="生物扫描",
        summary="对生物类目标效果更强。",
        bonus_family="living",
        clarity_bonus=0.07,
    ),
}


FREEZE_REGION_LABELS: dict[str, str] = {
    "upper-left": "左上区域",
    "center": "中央区域",
    "lower-right": "右下区域",
}


TARGETS: tuple[TargetDefinition, ...] = (
    TargetDefinition(
        label="猫",
        family="living",
        hint="谱带：生物 / 灵巧",
        accent="#f4c95d",
    ),
    TargetDefinition(
        label="狐狸",
        family="living",
        hint="谱带：生物 / 野性",
        accent="#ff8a5b",
    ),
    TargetDefinition(
        label="狼",
        family="living",
        hint="谱带：生物 / 掠食",
        accent="#8fd3ff",
    ),
    TargetDefinition(
        label="龙",
        family="living",
        hint="谱带：幻想 / 飞翼",
        accent="#ff6b6b",
    ),
    TargetDefinition(
        label="潜艇",
        family="machine",
        hint="谱带：机械 / 水下",
        accent="#56cfe1",
    ),
    TargetDefinition(
        label="悬浮摩托",
        family="machine",
        hint="谱带：机械 / 高速",
        accent="#ffd166",
    ),
    TargetDefinition(
        label="机器人",
        family="machine",
        hint="谱带：机械 / 类人",
        accent="#8ecae6",
    ),
    TargetDefinition(
        label="飞艇",
        family="machine",
        hint="谱带：机械 / 空中",
        accent="#cdb4db",
    ),
    TargetDefinition(
        label="城堡",
        family="structure",
        hint="谱带：建筑 / 防御",
        accent="#bcb8b1",
    ),
)
