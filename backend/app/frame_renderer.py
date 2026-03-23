from __future__ import annotations

import math
import random
import urllib.parse
from dataclasses import dataclass

from .game_data import TargetDefinition


DEFAULT_TOTAL_FRAMES = 24


@dataclass(frozen=True)
class TrajectoryVariant:
    key: str
    clarity_boost: float = 0.0
    noise_scale: float = 1.0
    jitter_scale: float = 1.0
    overlay_mode: str | None = None
    frozen_region: str | None = None


TRAJECTORY_VARIANTS: dict[str, TrajectoryVariant] = {
    "base": TrajectoryVariant(key="base"),
    "focus_generic": TrajectoryVariant(
        key="focus_generic",
        clarity_boost=0.12,
        noise_scale=0.82,
        jitter_scale=0.72,
        overlay_mode="generic",
    ),
    "focus_machine": TrajectoryVariant(
        key="focus_machine",
        clarity_boost=0.18,
        noise_scale=0.68,
        jitter_scale=0.62,
        overlay_mode="machine",
    ),
    "focus_living": TrajectoryVariant(
        key="focus_living",
        clarity_boost=0.18,
        noise_scale=0.68,
        jitter_scale=0.62,
        overlay_mode="living",
    ),
    "pulse_reveal": TrajectoryVariant(
        key="pulse_reveal",
        clarity_boost=0.16,
        noise_scale=0.74,
        jitter_scale=0.68,
        overlay_mode="pulse",
    ),
    "misguided": TrajectoryVariant(
        key="misguided",
        clarity_boost=-0.05,
        noise_scale=1.18,
        jitter_scale=1.25,
        overlay_mode="misguided",
    ),
    "corrupted": TrajectoryVariant(
        key="corrupted",
        clarity_boost=-0.08,
        noise_scale=1.28,
        jitter_scale=1.35,
        overlay_mode="corrupted",
    ),
    "freeze_upper_left": TrajectoryVariant(
        key="freeze_upper_left",
        clarity_boost=0.1,
        noise_scale=0.84,
        jitter_scale=0.78,
        frozen_region="upper-left",
    ),
    "freeze_center": TrajectoryVariant(
        key="freeze_center",
        clarity_boost=0.1,
        noise_scale=0.84,
        jitter_scale=0.78,
        frozen_region="center",
    ),
    "freeze_lower_right": TrajectoryVariant(
        key="freeze_lower_right",
        clarity_boost=0.1,
        noise_scale=0.84,
        jitter_scale=0.78,
        frozen_region="lower-right",
    ),
}


def generate_target_trajectories(
    target: TargetDefinition,
    total_frames: int = DEFAULT_TOTAL_FRAMES,
) -> dict[str, list[str]]:
    trajectories: dict[str, list[str]] = {}
    for variant_key in TRAJECTORY_VARIANTS:
        trajectories[variant_key] = [
            render_frame_data_uri(
                target=target,
                frame_index=frame_index,
                total_frames=total_frames,
                variant_key=variant_key,
            )
            for frame_index in range(total_frames)
        ]
    return trajectories


def render_frame_data_uri(
    target: TargetDefinition,
    frame_index: int,
    total_frames: int,
    variant_key: str,
) -> str:
    svg = render_frame_svg(
        target=target,
        frame_index=frame_index,
        total_frames=total_frames,
        variant_key=variant_key,
    )
    return f"data:image/svg+xml;utf8,{urllib.parse.quote(svg)}"


def render_frame_svg(
    target: TargetDefinition,
    frame_index: int,
    total_frames: int,
    variant_key: str,
) -> str:
    variant = TRAJECTORY_VARIANTS[variant_key]
    progress = frame_index / max(total_frames - 1, 1)
    clarity = _clamp(0.08 + progress * 0.72 + variant.clarity_boost, 0.05, 0.98)
    rng = random.Random(f"{target.label}:{variant_key}:{frame_index}")
    frozen_region = _region_bounds(variant.frozen_region)

    scene_markup = _draw_scene(
        target=target,
        clarity=clarity,
        variant=variant,
        progress=progress,
    )
    target_markup = _draw_target(
        target=target,
        clarity=clarity,
        jitter_scale=variant.jitter_scale,
        rng=rng,
    )
    noise_markup = _draw_noise(
        clarity=clarity,
        noise_scale=variant.noise_scale,
        rng=rng,
        frozen_region=frozen_region,
    )
    overlay_markup = _draw_overlay(variant=variant, clarity=clarity)
    foreground_markup = _draw_foreground(
        target=target,
        clarity=clarity,
        variant=variant,
    )

    return f"""
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" aria-label="离线去噪轨迹帧">
  <defs>
    <radialGradient id="bg" cx="50%" cy="42%" r="70%">
      <stop offset="0%" stop-color="#16303a" />
      <stop offset="55%" stop-color="#0b1720" />
      <stop offset="100%" stop-color="#05080d" />
    </radialGradient>
    <linearGradient id="beam" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#72d6c9" stop-opacity="0.0" />
      <stop offset="45%" stop-color="#72d6c9" stop-opacity="0.18" />
      <stop offset="100%" stop-color="#72d6c9" stop-opacity="0.0" />
    </linearGradient>
  </defs>
  <rect width="64" height="64" fill="url(#bg)" rx="6" />
  {scene_markup}
  <g stroke="#ffffff" stroke-opacity="0.04" stroke-width="0.45">
    <path d="M8 0V64M16 0V64M24 0V64M32 0V64M40 0V64M48 0V64M56 0V64" />
    <path d="M0 8H64M0 16H64M0 24H64M0 32H64M0 40H64M0 48H64M0 56H64" />
  </g>
  {noise_markup}
  {target_markup}
  {overlay_markup}
  {foreground_markup}
</svg>
""".strip()


def _draw_noise(
    clarity: float,
    noise_scale: float,
    rng: random.Random,
    frozen_region: tuple[int, int, int, int] | None,
) -> str:
    noise_count = int((70 * (1 - clarity)) * noise_scale) + 10
    fragments: list[str] = []

    for _ in range(noise_count):
        x1 = rng.uniform(4, 60)
        y1 = rng.uniform(4, 60)

        if frozen_region and _point_in_region(x1, y1, frozen_region) and rng.random() < 0.65:
            continue

        angle = rng.uniform(0, math.tau)
        length = rng.uniform(2.0, 6.8) * (1.1 - clarity) * noise_scale
        x2 = x1 + math.cos(angle) * length
        y2 = y1 + math.sin(angle) * length
        opacity = _clamp(0.12 + (1 - clarity) * 0.22 * noise_scale, 0.06, 0.34)
        fragments.append(
            "<line "
            f'x1="{x1:.2f}" y1="{y1:.2f}" '
            f'x2="{x2:.2f}" y2="{y2:.2f}" '
            'stroke="#bde0d6" '
            f'stroke-opacity="{opacity:.3f}" '
            'stroke-width="0.65" />'
        )

    return "<g>" + "".join(fragments) + "</g>"


def _draw_overlay(variant: TrajectoryVariant, clarity: float) -> str:
    fragments: list[str] = []

    if variant.overlay_mode == "generic":
        fragments.append(
            '<g fill="none" stroke="#f6bd60" stroke-opacity="0.22" stroke-width="0.7">'
            '<path d="M12 50L52 14" />'
            '<path d="M14 52L54 16" />'
            "</g>"
        )

    if variant.overlay_mode == "machine":
        fragments.append(
            '<g fill="none" stroke="#72d6c9" stroke-opacity="0.38" stroke-width="0.5">'
            '<circle cx="32" cy="32" r="21" />'
            '<circle cx="32" cy="32" r="12" />'
            '<path d="M32 7V15M32 49V57M7 32H15M49 32H57" />'
            "</g>"
        )

    if variant.overlay_mode == "living":
        fragments.append(
            '<g fill="none" stroke="#f6bd60" stroke-opacity="0.32" stroke-width="0.7">'
            '<path d="M18 44C26 34 38 34 46 44" />'
            '<path d="M20 20C24 12 40 12 44 20" />'
            "</g>"
        )

    if variant.overlay_mode == "pulse":
        fragments.append(
            '<g fill="none" stroke="#8fd3ff" stroke-opacity="0.34" stroke-width="0.8">'
            '<circle cx="32" cy="32" r="24" />'
            '<circle cx="32" cy="32" r="15" />'
            '<path d="M4 32H60M32 4V60" />'
            "</g>"
        )
        fragments.append(
            '<rect x="-10" y="26" width="84" height="12" fill="url(#beam)" />'
        )

    if variant.overlay_mode == "misguided":
        fragments.append(
            '<g fill="none" stroke="#ff7a7a" stroke-opacity="0.26" stroke-width="0.8">'
            '<path d="M16 16L48 48M48 16L16 48" />'
            '<circle cx="32" cy="32" r="18" />'
            "</g>"
        )

    if variant.overlay_mode == "corrupted":
        fragments.append(
            '<g fill="none" stroke="#ff7a7a" stroke-opacity="0.32" stroke-width="0.9">'
            '<path d="M8 18L22 14L36 18L52 11" />'
            '<path d="M12 43L28 39L41 44L56 40" />'
            '<path d="M14 10L18 54M48 8L44 56" />'
            "</g>"
        )
        fragments.append(
            '<g fill="#ff7a7a" fill-opacity="0.08">'
            '<rect x="0" y="0" width="64" height="6" />'
            '<rect x="0" y="58" width="64" height="6" />'
            "</g>"
        )

    if variant.frozen_region is not None:
        x, y, width, height = _region_bounds(variant.frozen_region)
        fragments.append(
            '<rect '
            f'x="{x}" y="{y}" width="{width}" height="{height}" '
            'rx="4" fill="#f6bd60" fill-opacity="0.08" '
            'stroke="#f6bd60" stroke-width="0.7" stroke-dasharray="2 2" />'
        )

    if clarity > 0.72:
        fragments.append(
            '<rect x="3" y="3" width="58" height="58" rx="7" '
            'fill="none" stroke="#f6bd60" stroke-opacity="0.18" stroke-width="0.8" />'
        )

    return "<g>" + "".join(fragments) + "</g>"


def _draw_target(
    target: TargetDefinition,
    clarity: float,
    jitter_scale: float,
    rng: random.Random,
) -> str:
    stroke_width = 1.2 + clarity * 0.9
    opacity = 0.18 + clarity * 0.78
    jitter = max(0.2, (1 - clarity) * 2.6 * jitter_scale)
    dx = rng.uniform(-jitter, jitter)
    dy = rng.uniform(-jitter, jitter)

    shapes = {
        "猫": (
            '<polygon points="20 24 25 16 29 24" />'
            '<polygon points="35 24 39 16 44 24" />'
            '<circle cx="32" cy="33" r="12" />'
            '<path d="M25 37H29M35 37H39M31 41L32 43L33 41" />'
            '<path d="M20 39H10M22 42H11M44 39H54M42 42H53" />'
        ),
        "狐狸": (
            '<polygon points="18 38 24 20 32 14 40 20 46 38 32 49" />'
            '<path d="M24 27L18 18M40 27L46 18M27 37H30M34 37H37" />'
            '<path d="M30 42L32 45L34 42" />'
        ),
        "狼": (
            '<path d="M16 42L21 22L28 17L34 24L41 17L48 23L50 42L35 47L22 47Z" />'
            '<path d="M24 34H28M36 34H40M30 40L32 43L34 40" />'
        ),
        "龙": (
            '<path d="M14 39C18 28 22 24 30 24C39 24 43 28 50 18" />'
            '<path d="M18 44C27 46 37 47 46 41" />'
            '<path d="M28 28L23 18L18 27M37 28L45 18L47 30" />'
            '<path d="M43 36L50 32L47 40" />'
        ),
        "潜艇": (
            '<path d="M14 37C14 30 20 26 28 26H40C48 26 53 31 53 37C53 43 48 47 40 47H28C20 47 14 43 14 37Z" />'
            '<path d="M29 26V19H39V26M39 19V14H45" />'
            '<circle cx="24" cy="37" r="2.5" />'
            '<circle cx="32" cy="37" r="2.5" />'
            '<circle cx="40" cy="37" r="2.5" />'
        ),
        "悬浮摩托": (
            '<path d="M15 38H49" />'
            '<path d="M24 31H39L46 38H32L24 31Z" />'
            '<circle cx="20" cy="42" r="5" />'
            '<circle cx="45" cy="42" r="5" />'
            '<path d="M33 31L36 24" />'
        ),
        "机器人": (
            '<rect x="19" y="18" width="26" height="24" rx="5" />'
            '<path d="M32 18V12M24 29H28M36 29H40M25 44V50M39 44V50M18 25L13 29M46 25L51 29" />'
            '<path d="M25 36C28 38 36 38 39 36" />'
        ),
        "飞艇": (
            '<ellipse cx="32" cy="24" rx="17" ry="10" />'
            '<path d="M24 34H40L37 42H27L24 34Z" />'
            '<path d="M16 24H10M48 24H54M38 17L44 13" />'
        ),
        "城堡": (
            '<path d="M16 47V27H22V33H26V24H38V33H42V27H48V47Z" />'
            '<path d="M30 47V36H34V47M16 27L20 23L24 27M26 24L30 20L34 24M38 24L42 20L46 24" />'
        ),
    }

    shape_markup = shapes[target.label]
    glow_group = (
        f'<g fill="{target.accent}" fill-opacity="{0.08 + clarity * 0.12:.3f}" '
        f'stroke="{target.accent}" stroke-opacity="{0.14 + clarity * 0.18:.3f}" '
        f'stroke-width="{stroke_width * 2.2:.2f}" '
        'stroke-linecap="round" stroke-linejoin="round" '
        f'transform="translate({dx:.2f} {dy:.2f})">{shape_markup}</g>'
    )
    fill_group = (
        f'<g fill="{target.accent}" fill-opacity="{0.06 + clarity * 0.18:.3f}" '
        'stroke="none" '
        f'transform="translate({dx:.2f} {dy:.2f})">{shape_markup}</g>'
    )
    stroke_group = (
        f'<g fill="none" stroke="{target.accent}" '
        f'stroke-width="{stroke_width:.2f}" '
        'stroke-linecap="round" stroke-linejoin="round" '
        f'stroke-opacity="{opacity:.3f}" '
        f'transform="translate({dx:.2f} {dy:.2f})">{shape_markup}</g>'
    )

    return glow_group + fill_group + stroke_group


def _draw_scene(
    target: TargetDefinition,
    clarity: float,
    variant: TrajectoryVariant,
    progress: float,
) -> str:
    scene_opacity = 0.1 + clarity * 0.16
    base_haze = (
        '<g fill="#72d6c9" fill-opacity="0.04">'
        '<circle cx="18" cy="14" r="10" />'
        '<circle cx="50" cy="18" r="12" />'
        "</g>"
    )

    scene_map = {
        "猫": (
            '<g fill="#effbf6" fill-opacity="{opacity}">'
            '<circle cx="49" cy="14" r="6" />'
            '<path d="M0 54L12 46L22 48L34 40L52 45L64 39V64H0Z" />'
            "</g>"
        ),
        "狐狸": (
            '<g fill="#ffb58a" fill-opacity="{opacity}">'
            '<path d="M0 55L11 47L22 50L32 45L46 47L64 42V64H0Z" />'
            '<circle cx="48" cy="12" r="5" />'
            "</g>"
        ),
        "狼": (
            '<g fill="#8fd3ff" fill-opacity="{opacity}">'
            '<circle cx="46" cy="13" r="6" />'
            '<path d="M0 56L16 46L28 48L43 42L64 48V64H0Z" />'
            "</g>"
        ),
        "龙": (
            '<g fill="#ff6b6b" fill-opacity="{opacity}">'
            '<path d="M0 58L12 45L25 52L36 39L48 47L64 34V64H0Z" />'
            '<circle cx="16" cy="18" r="4" />'
            '<circle cx="22" cy="12" r="2" />'
            "</g>"
        ),
        "潜艇": (
            '<g fill="#56cfe1" fill-opacity="{opacity}">'
            '<path d="M0 38C10 34 22 36 34 39C45 42 54 43 64 40V64H0Z" />'
            '<path d="M0 48C12 45 22 47 34 50C46 53 55 54 64 51V64H0Z" />'
            '<circle cx="14" cy="18" r="1.8" />'
            '<circle cx="18" cy="12" r="1.2" />'
            "</g>"
        ),
        "悬浮摩托": (
            '<g fill="#ffd166" fill-opacity="{opacity}">'
            '<path d="M0 58L18 44H46L64 34V64H0Z" />'
            '<path d="M6 42H22M30 36H46M40 30H58" stroke="#ffd166" stroke-opacity="{line_opacity}" stroke-width="1.2" />'
            "</g>"
        ),
        "机器人": (
            '<g fill="#8ecae6" fill-opacity="{opacity}">'
            '<rect x="8" y="11" width="10" height="14" rx="2" />'
            '<rect x="45" y="14" width="12" height="16" rx="2" />'
            '<path d="M0 58L15 47L28 51L44 43L64 45V64H0Z" />'
            "</g>"
        ),
        "飞艇": (
            '<g fill="#cdb4db" fill-opacity="{opacity}">'
            '<ellipse cx="18" cy="18" rx="8" ry="4" />'
            '<ellipse cx="48" cy="14" rx="10" ry="5" />'
            '<path d="M0 58L10 55L18 56L30 52L44 55L64 49V64H0Z" />'
            "</g>"
        ),
        "城堡": (
            '<g fill="#bcb8b1" fill-opacity="{opacity}">'
            '<circle cx="48" cy="13" r="6" />'
            '<path d="M0 57L8 51H18L24 47H33L39 51H48L55 46H64V64H0Z" />'
            "</g>"
        ),
    }

    scene_markup = scene_map[target.label].format(
        opacity=f"{scene_opacity:.3f}",
        line_opacity=f"{0.12 + progress * 0.12:.3f}",
    )

    if variant.overlay_mode == "corrupted":
        scene_markup += (
            '<g fill="#ff7a7a" fill-opacity="0.06">'
            '<polygon points="0 0 18 0 0 18" />'
            '<polygon points="64 64 46 64 64 46" />'
            "</g>"
        )

    return base_haze + scene_markup


def _draw_foreground(
    target: TargetDefinition,
    clarity: float,
    variant: TrajectoryVariant,
) -> str:
    shard_opacity = 0.06 + clarity * 0.08
    fragments = [
        '<g fill="#effbf6" fill-opacity="{opacity}">'
        '<polygon points="0 8 12 0 18 0 6 14" />'
        '<polygon points="64 12 52 0 46 0 58 18" />'
        '<polygon points="0 56 8 48 15 52 4 64 0 64" />'
        '<polygon points="64 52 58 46 50 49 59 64 64 64" />'
        "</g>".format(opacity=f"{shard_opacity:.3f}")
    ]

    if target.family == "machine":
        fragments.append(
            '<g fill="none" stroke="#72d6c9" stroke-opacity="0.18" stroke-width="0.5">'
            '<path d="M6 30H16M48 34H58M24 8V16M40 48V58" />'
            "</g>"
        )

    if variant.overlay_mode == "pulse":
        fragments.append(
            '<g fill="#8fd3ff" fill-opacity="0.08">'
            '<rect x="0" y="24" width="64" height="2" />'
            '<rect x="0" y="38" width="64" height="2" />'
            "</g>"
        )

    return "".join(fragments)


def _region_bounds(region: str | None) -> tuple[int, int, int, int] | None:
    if region == "upper-left":
        return (6, 6, 22, 22)
    if region == "center":
        return (18, 18, 28, 28)
    if region == "lower-right":
        return (36, 36, 22, 22)
    return None


def _point_in_region(
    x: float,
    y: float,
    region: tuple[int, int, int, int],
) -> bool:
    left, top, width, height = region
    return left <= x <= left + width and top <= y <= top + height


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))
