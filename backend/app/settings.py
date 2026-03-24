from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


DEFAULT_ALLOWED_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)
DEFAULT_ALLOWED_ORIGIN_REGEX = r"http://(localhost|127\.0\.0\.1):\d+"
DEFAULT_DB_PATH = Path.home() / ".noise-archaeologist" / "noise_archaeologist.db"
DEFAULT_JWT_SECRET = "noise-archaeologist-dev-secret"
DEFAULT_JWT_EXPIRES_SECONDS = 7 * 24 * 60 * 60


@dataclass(frozen=True)
class Settings:
    allowed_origins: tuple[str, ...] = DEFAULT_ALLOWED_ORIGINS
    allowed_origin_regex: str | None = DEFAULT_ALLOWED_ORIGIN_REGEX
    trajectory_manifest_path: Path | None = None
    db_path: Path = DEFAULT_DB_PATH
    jwt_secret: str = DEFAULT_JWT_SECRET
    jwt_expires_seconds: int = DEFAULT_JWT_EXPIRES_SECONDS

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
        raw_db_path = os.getenv("NOISE_ARCHAEOLOGIST_DB_PATH")
        db_path = (
            Path(raw_db_path).expanduser()
            if raw_db_path and raw_db_path.strip()
            else DEFAULT_DB_PATH
        )
        raw_jwt_secret = os.getenv("NOISE_ARCHAEOLOGIST_JWT_SECRET", DEFAULT_JWT_SECRET).strip()
        jwt_secret = raw_jwt_secret or DEFAULT_JWT_SECRET
        raw_jwt_expires_seconds = os.getenv("NOISE_ARCHAEOLOGIST_JWT_EXPIRES_SECONDS", "")
        try:
            jwt_expires_seconds = (
                int(raw_jwt_expires_seconds.strip())
                if raw_jwt_expires_seconds.strip()
                else DEFAULT_JWT_EXPIRES_SECONDS
            )
        except ValueError:
            jwt_expires_seconds = DEFAULT_JWT_EXPIRES_SECONDS

        return cls(
            allowed_origins=allowed_origins,
            allowed_origin_regex=allowed_origin_regex,
            trajectory_manifest_path=trajectory_manifest_path,
            db_path=db_path,
            jwt_secret=jwt_secret,
            jwt_expires_seconds=max(60, jwt_expires_seconds),
        )


def load_settings() -> Settings:
    return Settings.from_env()
