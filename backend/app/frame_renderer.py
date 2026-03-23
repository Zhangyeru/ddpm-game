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
    inversion_guidance_scale: float = 0.0
    guidance_scale: float = 1.2
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
        inversion_guidance_scale=0.0,
        guidance_scale=1.2,
    ),
    "focus_generic": TrajectoryVariant(
        key="focus_generic",
        prompt_suffix="sharp silhouette, clearer structure, higher detail",
        inversion_guidance_scale=0.15,
        guidance_scale=1.8,
    ),
    "focus_machine": TrajectoryVariant(
        key="focus_machine",
        prompt_suffix="mechanical details, metallic structure, crisp geometry",
        inversion_guidance_scale=0.2,
        guidance_scale=2.0,
    ),
    "focus_living": TrajectoryVariant(
        key="focus_living",
        prompt_suffix="organic details, fur, anatomy, natural texture",
        inversion_guidance_scale=0.2,
        guidance_scale=2.0,
    ),
    "pulse_reveal": TrajectoryVariant(
        key="pulse_reveal",
        prompt_suffix="crisp features, highly detailed, clearer edges",
        inversion_guidance_scale=0.25,
        guidance_scale=2.6,
    ),
    "misguided": TrajectoryVariant(
        key="misguided",
        prompt_suffix="wrong semantic emphasis, misleading details",
        inversion_guidance_scale=0.1,
        guidance_scale=2.2,
        wrong_family=True,
        negative_prompt="accurate category details, clean reconstruction",
    ),
    "corrupted": TrajectoryVariant(
        key="corrupted",
        prompt_suffix="unstable image, corrupted details, fragmented structure",
        inversion_guidance_scale=0.1,
        guidance_scale=1.6,
        corruption_noise_scale=0.03,
        corruption_noise_points=(0.2, 0.4, 0.6, 0.8),
    ),
    "freeze_upper_left": TrajectoryVariant(
        key="freeze_upper_left",
        inversion_guidance_scale=0.0,
        guidance_scale=1.1,
        frozen_region="upper-left",
        reference_lead_steps=8,
    ),
    "freeze_center": TrajectoryVariant(
        key="freeze_center",
        inversion_guidance_scale=0.0,
        guidance_scale=1.1,
        frozen_region="center",
        reference_lead_steps=10,
    ),
    "freeze_lower_right": TrajectoryVariant(
        key="freeze_lower_right",
        inversion_guidance_scale=0.0,
        guidance_scale=1.1,
        frozen_region="lower-right",
        reference_lead_steps=8,
    ),
}
