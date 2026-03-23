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
    signature: str
    accent: str


@dataclass(frozen=True)
class FreezeRegionDefinition:
    title: str
    summary: str


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


FREEZE_REGION_DEFINITIONS: dict[str, FreezeRegionDefinition] = {
    "upper-left": FreezeRegionDefinition(
        title="左上区域",
        summary="锁定画面的左上象限。",
    ),
    "center": FreezeRegionDefinition(
        title="中央区域",
        summary="锁定最核心的主体轮廓。",
    ),
    "lower-right": FreezeRegionDefinition(
        title="右下区域",
        summary="锁定画面的右下象限。",
    ),
}

FREEZE_REGION_LABELS: dict[str, str] = {
    region: definition.title
    for region, definition in FREEZE_REGION_DEFINITIONS.items()
}


TARGETS: tuple[TargetDefinition, ...] = (
    TargetDefinition(
        label="猫",
        family="living",
        hint="谱带：生物 / 灵巧",
        signature="特征签名：尖耳、胡须与圆形头部",
        accent="#f4c95d",
    ),
    TargetDefinition(
        label="狐狸",
        family="living",
        hint="谱带：生物 / 野性",
        signature="特征签名：三角脸、长吻与竖耳",
        accent="#ff8a5b",
    ),
    TargetDefinition(
        label="狼",
        family="living",
        hint="谱带：生物 / 掠食",
        signature="特征签名：前倾鼻梁、竖耳与掠食姿态",
        accent="#8fd3ff",
    ),
    TargetDefinition(
        label="龙",
        family="living",
        hint="谱带：幻想 / 飞翼",
        signature="特征签名：长躯干、翼膜与尾刺",
        accent="#ff6b6b",
    ),
    TargetDefinition(
        label="潜艇",
        family="machine",
        hint="谱带：机械 / 水下",
        signature="特征签名：艇身观察窗与潜望镜",
        accent="#56cfe1",
    ),
    TargetDefinition(
        label="悬浮摩托",
        family="machine",
        hint="谱带：机械 / 高速",
        signature="特征签名：双轮悬空、前低后高",
        accent="#ffd166",
    ),
    TargetDefinition(
        label="机器人",
        family="machine",
        hint="谱带：机械 / 类人",
        signature="特征签名：方形头部、天线与关节肢体",
        accent="#8ecae6",
    ),
    TargetDefinition(
        label="飞艇",
        family="machine",
        hint="谱带：机械 / 空中",
        signature="特征签名：气囊吊舱与尾翼",
        accent="#cdb4db",
    ),
    TargetDefinition(
        label="城堡",
        family="structure",
        hint="谱带：建筑 / 防御",
        signature="特征签名：塔楼、城垛与拱门",
        accent="#bcb8b1",
    ),
)
