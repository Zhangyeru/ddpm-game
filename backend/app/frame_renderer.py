from __future__ import annotations

from dataclasses import dataclass


DEFAULT_TOTAL_FRAMES = 24
FRAME_IMAGE_SIZE = (384, 384)
FRAME_OUTPUT_FORMAT = "WEBP"
FRAME_OUTPUT_SUFFIX = ".webp"


@dataclass(frozen=True)
class TrajectoryVariant:
    key: str
    clarity_boost: float = 0.0
    blur_scale: float = 1.0
    noise_scale: float = 1.0
    contrast_scale: float = 1.0
    saturation_scale: float = 1.0
    brightness_bias: float = 0.0
    tint_color: tuple[int, int, int] | None = None
    tint_strength: float = 0.0
    overlay_mode: str | None = None
    frozen_region: str | None = None


TRAJECTORY_VARIANTS: dict[str, TrajectoryVariant] = {
    "base": TrajectoryVariant(key="base"),
    "focus_generic": TrajectoryVariant(
        key="focus_generic",
        clarity_boost=0.12,
        blur_scale=0.78,
        noise_scale=0.7,
        contrast_scale=1.08,
        saturation_scale=1.04,
    ),
    "focus_machine": TrajectoryVariant(
        key="focus_machine",
        clarity_boost=0.18,
        blur_scale=0.64,
        noise_scale=0.58,
        contrast_scale=1.16,
        saturation_scale=0.98,
        tint_color=(74, 170, 210),
        tint_strength=0.08,
    ),
    "focus_living": TrajectoryVariant(
        key="focus_living",
        clarity_boost=0.18,
        blur_scale=0.62,
        noise_scale=0.56,
        contrast_scale=1.12,
        saturation_scale=1.12,
        tint_color=(243, 193, 94),
        tint_strength=0.08,
    ),
    "pulse_reveal": TrajectoryVariant(
        key="pulse_reveal",
        clarity_boost=0.16,
        blur_scale=0.7,
        noise_scale=0.6,
        contrast_scale=1.1,
        saturation_scale=1.06,
        overlay_mode="pulse",
    ),
    "misguided": TrajectoryVariant(
        key="misguided",
        clarity_boost=-0.06,
        blur_scale=1.15,
        noise_scale=1.22,
        contrast_scale=0.94,
        saturation_scale=0.88,
        tint_color=(200, 120, 50),
        tint_strength=0.14,
        overlay_mode="misguided",
    ),
    "corrupted": TrajectoryVariant(
        key="corrupted",
        clarity_boost=-0.1,
        blur_scale=1.28,
        noise_scale=1.38,
        contrast_scale=0.9,
        saturation_scale=0.82,
        brightness_bias=-0.04,
        tint_color=(160, 70, 70),
        tint_strength=0.2,
        overlay_mode="corrupted",
    ),
    "freeze_upper_left": TrajectoryVariant(
        key="freeze_upper_left",
        clarity_boost=0.08,
        blur_scale=0.86,
        noise_scale=0.82,
        frozen_region="upper-left",
    ),
    "freeze_center": TrajectoryVariant(
        key="freeze_center",
        clarity_boost=0.1,
        blur_scale=0.82,
        noise_scale=0.78,
        frozen_region="center",
    ),
    "freeze_lower_right": TrajectoryVariant(
        key="freeze_lower_right",
        clarity_boost=0.08,
        blur_scale=0.86,
        noise_scale=0.82,
        frozen_region="lower-right",
    ),
}
