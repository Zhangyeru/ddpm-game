from __future__ import annotations

import json
import sys
from pathlib import Path


CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = CURRENT_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.frame_renderer import DEFAULT_TOTAL_FRAMES, TRAJECTORY_VARIANTS, generate_target_trajectories
from app.game_data import TARGETS


def main() -> None:
    output_path = BACKEND_DIR / "assets" / "trajectories" / "manifest.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    manifest = {
        "version": 1,
        "total_frames": DEFAULT_TOTAL_FRAMES,
        "variant_keys": list(TRAJECTORY_VARIANTS.keys()),
        "targets": {
            target.label: {
                "family": target.family,
                "hint": target.hint,
                "variants": generate_target_trajectories(target, DEFAULT_TOTAL_FRAMES),
            }
            for target in TARGETS
        },
    }

    output_path.write_text(
        json.dumps(manifest, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    print(f"已生成离线轨迹清单：{output_path}")


if __name__ == "__main__":
    main()
