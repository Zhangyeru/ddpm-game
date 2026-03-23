from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from PIL import Image, ImageOps


CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CURRENT_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.diffusion_trajectory import (
    DiffusionTrajectoryGenerator,
    GenerationConfig,
    resolve_variant_plan,
)
from app.frame_renderer import (
    DEFAULT_MODEL_ID,
    DEFAULT_TOTAL_FRAMES,
    FRAME_IMAGE_SIZE,
    FRAME_OUTPUT_FORMAT,
    FRAME_OUTPUT_SUFFIX,
    TRAJECTORY_VARIANTS,
)
from app.game_data import TARGETS


SUPPORTED_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


def main() -> None:
    args = parse_args()
    selected_targets = _select_targets(args.targets)
    selected_variant_keys = _select_variant_keys(args.variant_keys)

    assets_dir = BACKEND_DIR / "assets"
    source_root = assets_dir / "source-images"
    output_root = (
        Path(args.output_root).expanduser().resolve()
        if args.output_root
        else assets_dir / "trajectories"
    )
    generated_root = output_root / "generated"
    manifest_path = output_root / "manifest.json"

    missing_assets: list[str] = []
    for target in selected_targets:
        source_dir = source_root / target.asset_key
        images = _list_source_images(source_dir)
        if len(images) < 1:
            missing_assets.append(f"{target.label}({target.asset_key}) 没有源图。")

    if missing_assets:
        details = "\n".join(f"- {item}" for item in missing_assets)
        raise SystemExit(f"无法生成轨迹资源：\n{details}")

    generator = DiffusionTrajectoryGenerator(
        GenerationConfig(
            model_id=args.model_id,
            num_steps=args.num_steps,
            device=args.device,
        )
    )

    if generated_root.exists() and not args.keep_existing:
        shutil.rmtree(generated_root)
    generated_root.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, object] = {
        "version": 3,
        "total_frames": args.num_steps,
        "variant_keys": list(selected_variant_keys),
        "generator": {
            "model_id": args.model_id,
            "scheduler": "ddim_inversion",
            "num_steps": args.num_steps,
            "device_mode": args.device,
        },
        "targets": {},
    }

    for target in selected_targets:
        print(f"生成目标：{target.asset_key}")
        source_images = _list_source_images(source_root / target.asset_key)
        samples_payload: dict[str, object] = {}
        chosen_sample_ids = set(_parse_csv(args.sample_ids))

        for sample_index, source_path in enumerate(source_images, start=1):
            sample_id = f"sample-{sample_index:02d}"
            if chosen_sample_ids and sample_id not in chosen_sample_ids:
                continue

            print(f"  样本：{sample_id}")
            base_image = _load_source_image(source_path)
            variants_payload: dict[str, list[str]] = {}
            prompts_payload: dict[str, str] = {}

            for variant_key in selected_variant_keys:
                print(f"    变体：{variant_key}")
                variant = TRAJECTORY_VARIANTS[variant_key]
                prompts_payload[variant_key] = resolve_variant_plan(
                    target=target,
                    variant=variant,
                ).prompt
                frame_dir = generated_root / target.asset_key / sample_id / variant_key
                frame_dir.mkdir(parents=True, exist_ok=True)
                frames = generator.generate_variant_frames(
                    image=base_image,
                    target=target,
                    sample_id=sample_id,
                    variant=variant,
                )
                frame_paths: list[str] = []
                for frame_index, frame in enumerate(frames):
                    frame_path = frame_dir / f"{frame_index:03d}{FRAME_OUTPUT_SUFFIX}"
                    frame.save(frame_path, FRAME_OUTPUT_FORMAT, quality=62, method=4)
                    frame_paths.append(frame_path.relative_to(output_root).as_posix())
                variants_payload[variant_key] = frame_paths

            if variants_payload:
                samples_payload[sample_id] = {
                    "source_path": f"../source-images/{target.asset_key}/{source_path.name}",
                    "prompts": prompts_payload,
                    "variants": variants_payload,
                }

        if samples_payload:
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
    print(f"已生成真实扩散轨迹清单：{manifest_path}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate real diffusion denoise trajectories.")
    parser.add_argument("--device", default="auto", choices=("auto", "cpu", "cuda"))
    parser.add_argument("--model-id", default=DEFAULT_MODEL_ID)
    parser.add_argument("--num-steps", type=int, default=DEFAULT_TOTAL_FRAMES)
    parser.add_argument("--targets", default="")
    parser.add_argument("--sample-ids", default="")
    parser.add_argument("--variant-keys", default="")
    parser.add_argument("--output-root", default="")
    parser.add_argument("--keep-existing", action="store_true")
    return parser.parse_args()


def _parse_csv(raw: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in raw.split(",") if part.strip())


def _select_targets(raw: str):
    selected = set(_parse_csv(raw))
    if not selected:
        return TARGETS
    return tuple(target for target in TARGETS if target.asset_key in selected)


def _select_variant_keys(raw: str) -> tuple[str, ...]:
    selected = _parse_csv(raw)
    if not selected:
        return tuple(TRAJECTORY_VARIANTS.keys())
    invalid = [key for key in selected if key not in TRAJECTORY_VARIANTS]
    if invalid:
        raise SystemExit(f"未知变体：{', '.join(invalid)}")
    return selected


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


if __name__ == "__main__":
    main()
