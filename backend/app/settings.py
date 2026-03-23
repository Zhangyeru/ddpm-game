from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


DEFAULT_ALLOWED_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)
DEFAULT_ALLOWED_ORIGIN_REGEX = r"http://(localhost|127\.0\.0\.1):\d+"


@dataclass(frozen=True)
class Settings:
    allowed_origins: tuple[str, ...] = DEFAULT_ALLOWED_ORIGINS
    allowed_origin_regex: str | None = DEFAULT_ALLOWED_ORIGIN_REGEX
    trajectory_manifest_path: Path | None = None

    @classmethod
    def from_env(cls) -> Settings:
        raw_origins = os.getenv("NOISE_ARCHAEOLOGIST_ALLOWED_ORIGINS", "")
        allowed_origins = tuple(
            origin.strip()
            for origin in raw_origins.split(",")
            if origin.strip()
        )
        if not allowed_origins:
            allowed_origins = DEFAULT_ALLOWED_ORIGINS

        raw_regex = os.getenv("NOISE_ARCHAEOLOGIST_ALLOWED_ORIGIN_REGEX")
        if raw_regex is None:
            allowed_origin_regex = DEFAULT_ALLOWED_ORIGIN_REGEX
        else:
            allowed_origin_regex = raw_regex.strip() or None

        raw_manifest_path = os.getenv("NOISE_ARCHAEOLOGIST_TRAJECTORY_MANIFEST")
        trajectory_manifest_path = (
            Path(raw_manifest_path).expanduser()
            if raw_manifest_path and raw_manifest_path.strip()
            else None
        )

        return cls(
            allowed_origins=allowed_origins,
            allowed_origin_regex=allowed_origin_regex,
            trajectory_manifest_path=trajectory_manifest_path,
        )


def load_settings() -> Settings:
    return Settings.from_env()
