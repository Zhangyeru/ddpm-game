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
    asset_key: str
    label: str
    prompt_token: str
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
        asset_key="cat",
        label="猫",
        prompt_token="cat",
        family="living",
        hint="谱带：生物 / 家养",
        signature="特征签名：尖耳、胡须与圆形头部",
        accent="#f4c95d",
    ),
    TargetDefinition(
        asset_key="dog",
        label="狗",
        prompt_token="dog",
        family="living",
        hint="谱带：生物 / 伴侣",
        signature="特征签名：下垂耳、长吻与友好面部轮廓",
        accent="#ff9f68",
    ),
    TargetDefinition(
        asset_key="horse",
        label="马",
        prompt_token="horse",
        family="living",
        hint="谱带：生物 / 牧场",
        signature="特征签名：长脸、鬃毛与高挑四肢",
        accent="#c7a27c",
    ),
    TargetDefinition(
        asset_key="eagle",
        label="鹰",
        prompt_token="eagle",
        family="living",
        hint="谱带：生物 / 猛禽",
        signature="特征签名：钩状喙、张开双翼与锐利眼部轮廓",
        accent="#ffb35c",
    ),
    TargetDefinition(
        asset_key="motorcycle",
        label="摩托车",
        prompt_token="motorcycle",
        family="machine",
        hint="谱带：机械 / 公路",
        signature="特征签名：车把、外露车轮与纵向车身",
        accent="#56cfe1",
    ),
    TargetDefinition(
        asset_key="bicycle",
        label="自行车",
        prompt_token="bicycle",
        family="machine",
        hint="谱带：机械 / 骑行",
        signature="特征签名：细车架、车把与双轮结构",
        accent="#ffd166",
    ),
    TargetDefinition(
        asset_key="train",
        label="火车",
        prompt_token="train",
        family="machine",
        hint="谱带：机械 / 轨道",
        signature="特征签名：长车厢、前端车头与轨道场景",
        accent="#8ecae6",
    ),
    TargetDefinition(
        asset_key="airplane",
        label="飞机",
        prompt_token="airplane",
        family="machine",
        hint="谱带：机械 / 航空",
        signature="特征签名：机翼、尾翼与细长机身",
        accent="#cdb4db",
    ),
    TargetDefinition(
        asset_key="castle",
        label="城堡",
        prompt_token="castle",
        family="structure",
        hint="谱带：建筑 / 防御",
        signature="特征签名：塔楼、城垛与拱门",
        accent="#bcb8b1",
    ),
    TargetDefinition(
        asset_key="lighthouse",
        label="灯塔",
        prompt_token="lighthouse",
        family="structure",
        hint="谱带：建筑 / 海岸",
        signature="特征签名：高塔、灯室与临海轮廓",
        accent="#a3cef1",
    ),
)
