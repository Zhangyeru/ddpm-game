from __future__ import annotations

import json
from pathlib import Path


class TrajectoryStore:
    def __init__(self, manifest_path: Path | None = None) -> None:
        self.manifest_path = manifest_path or (
            Path(__file__).resolve().parent.parent
            / "assets"
            / "trajectories"
            / "manifest.json"
        )
        data = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        self.total_frames = int(data["total_frames"])
        self.variant_keys = tuple(data["variant_keys"])
        self.targets: dict[str, dict[str, list[str]]] = {
            label: target_payload["variants"]
            for label, target_payload in data["targets"].items()
        }

    def get_frame(self, target_label: str, variant_key: str, frame_index: int) -> str:
        variants = self.targets[target_label]
        frames = variants.get(variant_key) or variants["base"]
        clamped_index = max(0, min(frame_index, len(frames) - 1))
        return frames[clamped_index]

