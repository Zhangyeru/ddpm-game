from __future__ import annotations

import json
import mimetypes
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FrameAsset:
    path: Path
    media_type: str

    def read_bytes(self) -> bytes:
        return self.path.read_bytes()


class TrajectoryStore:
    def __init__(self, manifest_path: Path | None = None) -> None:
        self.manifest_path = manifest_path or (
            Path(__file__).resolve().parent.parent
            / "assets"
            / "trajectories"
            / "manifest.json"
        )
        self.base_dir = self.manifest_path.parent
        data = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        if int(data.get("version", 0)) < 2:
            raise ValueError("轨迹清单版本过旧，请重新生成真实图片轨迹资源。")

        self.total_frames = int(data["total_frames"])
        self.variant_keys = tuple(data["variant_keys"])
        self.targets: dict[str, dict[str, object]] = data["targets"]
        self.target_labels = tuple(self.targets.keys())

    def has_target(self, target_label: str) -> bool:
        return target_label in self.targets

    def sample_ids_for_target(self, target_label: str) -> tuple[str, ...]:
        target_payload = self.targets[target_label]
        samples = target_payload["samples"]
        return tuple(samples.keys())  # type: ignore[return-value]

    def get_frame(
        self,
        target_label: str,
        sample_id: str,
        variant_key: str,
        frame_index: int,
    ) -> FrameAsset:
        target_payload = self.targets[target_label]
        samples = target_payload["samples"]  # type: ignore[assignment]
        sample_payload = samples[sample_id]
        variants = sample_payload["variants"]
        frames = variants.get(variant_key) or variants["base"]
        clamped_index = max(0, min(frame_index, len(frames) - 1))
        relative_path = Path(frames[clamped_index])
        full_path = self.base_dir / relative_path
        media_type = mimetypes.guess_type(full_path.name)[0] or "application/octet-stream"
        return FrameAsset(path=full_path, media_type=media_type)
