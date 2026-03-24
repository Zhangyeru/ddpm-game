from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.app.settings import (
    DEFAULT_ALLOWED_ORIGIN_REGEX,
    DEFAULT_ALLOWED_ORIGINS,
    DEFAULT_DB_PATH,
    DEFAULT_JWT_EXPIRES_SECONDS,
    DEFAULT_JWT_SECRET,
    Settings,
)


class SettingsTest(unittest.TestCase):
    def test_from_env_uses_defaults(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings.from_env()

        self.assertEqual(settings.allowed_origins, DEFAULT_ALLOWED_ORIGINS)
        self.assertEqual(settings.allowed_origin_regex, DEFAULT_ALLOWED_ORIGIN_REGEX)
        self.assertIsNone(settings.trajectory_manifest_path)
        self.assertEqual(settings.db_path, DEFAULT_DB_PATH)
        self.assertEqual(settings.jwt_secret, DEFAULT_JWT_SECRET)
        self.assertEqual(settings.jwt_expires_seconds, DEFAULT_JWT_EXPIRES_SECONDS)

    def test_from_env_parses_custom_values(self) -> None:
        with patch.dict(
            os.environ,
            {
                "NOISE_ARCHAEOLOGIST_ALLOWED_ORIGINS": "https://demo.example, https://admin.example",
                "NOISE_ARCHAEOLOGIST_ALLOWED_ORIGIN_REGEX": "",
                "NOISE_ARCHAEOLOGIST_TRAJECTORY_MANIFEST": "~/trajectories.json",
                "NOISE_ARCHAEOLOGIST_DB_PATH": "~/noise.sqlite3",
                "NOISE_ARCHAEOLOGIST_JWT_SECRET": "custom-secret",
                "NOISE_ARCHAEOLOGIST_JWT_EXPIRES_SECONDS": "3600",
            },
            clear=True,
        ):
            settings = Settings.from_env()

        self.assertEqual(
            settings.allowed_origins,
            ("https://demo.example", "https://admin.example"),
        )
        self.assertIsNone(settings.allowed_origin_regex)
        self.assertEqual(
            settings.trajectory_manifest_path,
            Path("~/trajectories.json").expanduser(),
        )
        self.assertEqual(settings.db_path, Path("~/noise.sqlite3").expanduser())
        self.assertEqual(settings.jwt_secret, "custom-secret")
        self.assertEqual(settings.jwt_expires_seconds, 3600)


if __name__ == "__main__":
    unittest.main()
