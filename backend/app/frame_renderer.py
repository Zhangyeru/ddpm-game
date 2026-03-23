from __future__ import annotations

from dataclasses import dataclass


DEFAULT_TOTAL_FRAMES = 100
FRAME_IMAGE_SIZE = (384, 384)
FRAME_OUTPUT_FORMAT = "WEBP"
FRAME_OUTPUT_SUFFIX = ".webp"
DEFAULT_MODEL_ID = "runwayml/stable-diffusion-v1-5"


@dataclass(frozen=True)
class TrajectoryVariant:
    key: str
    prompt_suffix: str = ""
    guidance_scale: float = 5.0
    negative_prompt: str | None = None
    wrong_family: bool = False
    corruption_noise_scale: float = 0.0
    corruption_noise_points: tuple[float, ...] = ()
    frozen_region: str | None = None
    reference_lead_steps: int = 0


TRAJECTORY_VARIANTS: dict[str, TrajectoryVariant] = {
    "base": TrajectoryVariant(
        key="base",
        prompt_suffix="high quality photo, natural lighting",
        guidance_scale=5.0,
    ),
    "focus_generic": TrajectoryVariant(
        key="focus_generic",
        prompt_suffix="sharp silhouette, clearer structure, higher detail",
        guidance_scale=6.5,
    ),
    "focus_machine": TrajectoryVariant(
        key="focus_machine",
        prompt_suffix="mechanical details, metallic structure, crisp geometry",
        guidance_scale=7.0,
    ),
    "focus_living": TrajectoryVariant(
        key="focus_living",
        prompt_suffix="organic details, fur, anatomy, natural texture",
        guidance_scale=7.0,
    ),
    "pulse_reveal": TrajectoryVariant(
        key="pulse_reveal",
        prompt_suffix="crisp features, highly detailed, clearer edges",
        guidance_scale=8.0,
    ),
    "misguided": TrajectoryVariant(
        key="misguided",
        prompt_suffix="wrong semantic emphasis, misleading details",
        guidance_scale=7.0,
        wrong_family=True,
        negative_prompt="accurate category details, clean reconstruction",
    ),
    "corrupted": TrajectoryVariant(
        key="corrupted",
        prompt_suffix="unstable image, corrupted details, fragmented structure",
        guidance_scale=6.0,
        corruption_noise_scale=0.03,
        corruption_noise_points=(0.2, 0.4, 0.6, 0.8),
    ),
    "freeze_upper_left": TrajectoryVariant(
        key="freeze_upper_left",
        frozen_region="upper-left",
        reference_lead_steps=8,
    ),
    "freeze_center": TrajectoryVariant(
        key="freeze_center",
        frozen_region="center",
        reference_lead_steps=10,
    ),
    "freeze_lower_right": TrajectoryVariant(
        key="freeze_lower_right",
        frozen_region="lower-right",
        reference_lead_steps=8,
    ),
}
