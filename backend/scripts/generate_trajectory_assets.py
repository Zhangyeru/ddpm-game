from __future__ import annotations

import hashlib
import json
import random
import shutil
import sys
from dataclasses import replace
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter, ImageOps


CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CURRENT_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.frame_renderer import (
    DEFAULT_TOTAL_FRAMES,
    FRAME_IMAGE_SIZE,
    FRAME_OUTPUT_FORMAT,
    FRAME_OUTPUT_SUFFIX,
    TRAJECTORY_VARIANTS,
    TrajectoryVariant,
)
from app.game_data import TARGETS, TargetDefinition


SUPPORTED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


def main() -> None:
    assets_dir = BACKEND_DIR / "assets"
    source_root = assets_dir / "source-images"
    output_root = assets_dir / "trajectories"
    generated_root = output_root / "generated"
    manifest_path = output_root / "manifest.json"

    missing_assets: list[str] = []
    for target in TARGETS:
        source_dir = source_root / target.asset_key
        images = _list_source_images(source_dir)
        if len(images) < 3:
            missing_assets.append(f"{target.label}({target.asset_key}) 缺少素材，至少需要 3 张。")

    if missing_assets:
        details = "\n".join(f"- {item}" for item in missing_assets)
        raise SystemExit(f"无法生成轨迹资源：\n{details}")

    if generated_root.exists():
        shutil.rmtree(generated_root)
    generated_root.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, object] = {
        "version": 2,
        "total_frames": DEFAULT_TOTAL_FRAMES,
        "variant_keys": list(TRAJECTORY_VARIANTS.keys()),
        "targets": {},
    }

    for target in TARGETS:
        source_dir = source_root / target.asset_key
        source_images = _list_source_images(source_dir)
        samples_payload: dict[str, object] = {}

        for sample_index, source_path in enumerate(source_images, start=1):
            sample_id = f"sample-{sample_index:02d}"
            base_image = _load_source_image(source_path)
            variants_payload: dict[str, list[str]] = {}

            for variant_key, variant in TRAJECTORY_VARIANTS.items():
                frame_paths: list[str] = []
                frame_dir = generated_root / target.asset_key / sample_id / variant_key
                frame_dir.mkdir(parents=True, exist_ok=True)

                for frame_index in range(DEFAULT_TOTAL_FRAMES):
                    frame = _render_frame(
                        base_image=base_image,
                        target=target,
                        sample_id=sample_id,
                        variant=variant,
                        frame_index=frame_index,
                        total_frames=DEFAULT_TOTAL_FRAMES,
                    )
                    frame_path = frame_dir / f"{frame_index:02d}{FRAME_OUTPUT_SUFFIX}"
                    frame.save(frame_path, FRAME_OUTPUT_FORMAT, quality=62, method=4)
                    frame_paths.append(frame_path.relative_to(output_root).as_posix())

                variants_payload[variant_key] = frame_paths

            samples_payload[sample_id] = {
                "source_path": f"../source-images/{target.asset_key}/{source_path.name}",
                "variants": variants_payload,
            }

        manifest["targets"][target.label] = {
            "asset_key": target.asset_key,
            "family": target.family,
            "hint": target.hint,
            "signature": target.signature,
            "samples": samples_payload,
        }

    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"已生成真实图片轨迹清单：{manifest_path}")


def _list_source_images(source_dir: Path) -> list[Path]:
    if not source_dir.exists():
        return []
    return sorted(
        path
        for path in source_dir.iterdir()
        if path.is_file() and path.suffix.lower() in SUPPORTED_IMAGE_SUFFIXES
    )


def _load_source_image(source_path: Path) -> Image.Image:
    with Image.open(source_path) as image:
        return ImageOps.fit(
            image.convert("RGB"),
            FRAME_IMAGE_SIZE,
            method=Image.Resampling.LANCZOS,
        )


def _render_frame(
    *,
    base_image: Image.Image,
    target: TargetDefinition,
    sample_id: str,
    variant: TrajectoryVariant,
    frame_index: int,
    total_frames: int,
) -> Image.Image:
    progress = frame_index / max(total_frames - 1, 1)
    clarity = _clamp(0.04 + progress * 0.86 + variant.clarity_boost, 0.02, 1.0)
    rng = random.Random(_seed_for(target.asset_key, sample_id, variant.key, frame_index))

    frame = _apply_base_adjustments(base_image, clarity, variant)
    frame = _apply_tint(frame, clarity, variant)
    frame = _apply_noise(frame, clarity, variant, rng)
    frame = _apply_occlusions(frame, clarity, variant, rng)

    if variant.overlay_mode is not None:
        frame = _apply_overlay_mode(frame, clarity, variant, rng)

    if variant.frozen_region is not None:
        frame = _apply_frozen_region(base_image, frame, clarity, variant, rng)

    if clarity > 0.72:
        frame = frame.filter(ImageFilter.UnsharpMask(radius=1.4, percent=160, threshold=3))

    return ImageOps.autocontrast(frame, cutoff=0.4)


def _apply_base_adjustments(
    base_image: Image.Image,
    clarity: float,
    variant: TrajectoryVariant,
) -> Image.Image:
    frame = base_image.copy()
    blur_radius = max(0.0, (20.0 * ((1.0 - clarity) ** 1.55) * variant.blur_scale) - 0.2)
    if blur_radius > 0:
        frame = frame.filter(ImageFilter.GaussianBlur(blur_radius))

    frame = ImageEnhance.Color(frame).enhance(
        _clamp((0.24 + clarity * 0.92) * variant.saturation_scale, 0.12, 1.45)
    )
    frame = ImageEnhance.Contrast(frame).enhance(
        _clamp((0.56 + clarity * 0.72) * variant.contrast_scale, 0.3, 1.55)
    )
    frame = ImageEnhance.Brightness(frame).enhance(
        _clamp(0.74 + clarity * 0.26 + variant.brightness_bias, 0.55, 1.25)
    )
    frame = ImageEnhance.Sharpness(frame).enhance(_clamp(0.18 + clarity * 2.4, 0.12, 2.8))
    return frame


def _apply_tint(
    image: Image.Image,
    clarity: float,
    variant: TrajectoryVariant,
) -> Image.Image:
    if variant.tint_color is None or variant.tint_strength <= 0:
        return image

    tint = Image.new("RGB", image.size, variant.tint_color)
    alpha = _clamp(variant.tint_strength * (1.08 - clarity), 0.0, 0.28)
    return Image.blend(image, tint, alpha)


def _apply_noise(
    image: Image.Image,
    clarity: float,
    variant: TrajectoryVariant,
    rng: random.Random,
) -> Image.Image:
    if clarity >= 0.98:
        return image

    amount = _clamp((1.0 - clarity) ** 1.18 * variant.noise_scale, 0.0, 1.2)
    coarse_noise = _noise_layer(image.size, rng, 48, 48)
    fine_noise = _noise_layer(image.size, rng, 96, 96)

    coarse = ImageOps.colorize(coarse_noise, (10, 20, 24), (240, 245, 245))
    fine = ImageOps.colorize(fine_noise, (0, 5, 10), (255, 255, 255))
    mixed_noise = Image.blend(coarse, fine, 0.4)
    mixed_noise = ImageEnhance.Contrast(mixed_noise).enhance(1.5)

    return Image.blend(image, mixed_noise, _clamp(0.48 * amount, 0.0, 0.56))


def _apply_occlusions(
    image: Image.Image,
    clarity: float,
    variant: TrajectoryVariant,
    rng: random.Random,
) -> Image.Image:
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    width, height = image.size
    blocks = int(14 * (1.0 - clarity) * max(0.6, variant.noise_scale)) + 2

    for _ in range(blocks):
        block_width = rng.randint(max(24, width // 12), max(40, width // 4))
        block_height = rng.randint(max(24, height // 12), max(40, height // 4))
        x0 = rng.randint(0, max(0, width - block_width))
        y0 = rng.randint(0, max(0, height - block_height))
        alpha = int(_clamp(25 + (1.0 - clarity) * 125, 18, 160))
        fill = (
            rng.randint(0, 18),
            rng.randint(10, 36),
            rng.randint(16, 44),
            alpha,
        )
        if rng.random() < 0.45:
            draw.ellipse((x0, y0, x0 + block_width, y0 + block_height), fill=fill)
        else:
            draw.rounded_rectangle(
                (x0, y0, x0 + block_width, y0 + block_height),
                radius=rng.randint(6, 20),
                fill=fill,
            )

    return Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")


def _apply_overlay_mode(
    image: Image.Image,
    clarity: float,
    variant: TrajectoryVariant,
    rng: random.Random,
) -> Image.Image:
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    width, height = image.size

    if variant.overlay_mode == "pulse":
        mask = Image.new("L", image.size, 0)
        mask_draw = ImageDraw.Draw(mask)
        radius = int(min(width, height) * (0.18 + clarity * 0.18))
        center = (width // 2, height // 2)
        mask_draw.ellipse(
            (center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius),
            fill=int(_clamp(110 + clarity * 70, 90, 170)),
        )
        mask = mask.filter(ImageFilter.GaussianBlur(radius=max(6, width // 18)))
        bright = ImageEnhance.Contrast(image).enhance(1.18)
        bright = ImageEnhance.Sharpness(bright).enhance(1.35)
        image = Image.composite(bright, image, mask)

    elif variant.overlay_mode == "misguided":
        lines = 7
        for _ in range(lines):
            y0 = rng.randint(0, height)
            y1 = y0 + rng.randint(-height // 8, height // 8)
            draw.line(
                ((0, y0), (width, y1)),
                fill=(240, 170, 70, int(_clamp(40 + (1.0 - clarity) * 60, 28, 96))),
                width=rng.randint(2, 5),
            )

    elif variant.overlay_mode == "corrupted":
        segments = 12
        for _ in range(segments):
            x0 = rng.randint(0, width)
            y0 = rng.randint(0, height)
            x1 = x0 + rng.randint(-width // 5, width // 5)
            y1 = y0 + rng.randint(-height // 5, height // 5)
            draw.line(
                ((x0, y0), (x1, y1)),
                fill=(170, 50, 50, int(_clamp(60 + (1.0 - clarity) * 80, 42, 120))),
                width=rng.randint(2, 6),
            )
        shifted = ImageChops.offset(image, width // 60, 0)
        image = Image.blend(image, shifted, 0.12)

    return Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")


def _apply_frozen_region(
    base_image: Image.Image,
    image: Image.Image,
    clarity: float,
    variant: TrajectoryVariant,
    rng: random.Random,
) -> Image.Image:
    reveal_variant = replace(
        variant,
        clarity_boost=variant.clarity_boost + 0.22,
        blur_scale=max(0.45, variant.blur_scale * 0.62),
        noise_scale=max(0.4, variant.noise_scale * 0.58),
        tint_strength=max(0.0, variant.tint_strength * 0.8),
        frozen_region=None,
    )
    revealed = _apply_base_adjustments(base_image, _clamp(clarity + 0.24, 0.02, 1.0), reveal_variant)
    revealed = _apply_tint(revealed, clarity, reveal_variant)
    revealed = _apply_noise(revealed, _clamp(clarity + 0.18, 0.02, 1.0), reveal_variant, rng)

    mask = _region_mask(image.size, variant.frozen_region or "center")
    return Image.composite(revealed, image, mask)


def _noise_layer(
    size: tuple[int, int],
    rng: random.Random,
    grid_width: int,
    grid_height: int,
) -> Image.Image:
    noise = Image.frombytes("L", (grid_width, grid_height), rng.randbytes(grid_width * grid_height))
    return noise.resize(size, Image.Resampling.BICUBIC)


def _region_mask(size: tuple[int, int], region: str) -> Image.Image:
    width, height = size
    if region == "upper-left":
        box = (0, 0, int(width * 0.56), int(height * 0.56))
    elif region == "lower-right":
        box = (int(width * 0.44), int(height * 0.44), width, height)
    else:
        box = (
            int(width * 0.22),
            int(height * 0.22),
            int(width * 0.78),
            int(height * 0.78),
        )

    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle(box, radius=max(18, width // 14), fill=220)
    return mask.filter(ImageFilter.GaussianBlur(radius=max(12, width // 18)))


def _seed_for(*parts: object) -> int:
    payload = "::".join(str(part) for part in parts).encode("utf-8")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


if __name__ == "__main__":
    main()
