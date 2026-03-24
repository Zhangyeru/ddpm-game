from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

import sqlite3
from fastapi.testclient import TestClient

from backend.app.auth import PlayerCampaignProgress, SQLiteAuthStore
from backend.app.main import create_app
from backend.app.settings import Settings


def make_test_client(temp_dir: str) -> tuple[TestClient, object]:
    app = create_app(
        Settings(
            db_path=Path(temp_dir) / "auth.sqlite3",
            jwt_secret="test-secret",
            jwt_expires_seconds=3600,
        )
    )
    return TestClient(app), app.state.service


def test_register_returns_token_and_progression() -> None:
    with TemporaryDirectory() as temp_dir:
        client, _ = make_test_client(temp_dir)

        response = client.post(
            "/api/auth/register",
            json={"username": "tester_01", "password": "password123"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["token_type"] == "bearer"
        assert payload["user"]["username"] == "tester_01"
        assert payload["progression"]["current_level_id"] == "chapter-1-level-1"
        assert payload["progression"]["campaign_total_score"] == 0
        assert payload["access_token"]


def test_register_rejects_duplicate_username() -> None:
    with TemporaryDirectory() as temp_dir:
        client, _ = make_test_client(temp_dir)

        first = client.post(
            "/api/auth/register",
            json={"username": "tester_01", "password": "password123"},
        )
        second = client.post(
            "/api/auth/register",
            json={"username": "tester_01", "password": "password123"},
        )

        assert first.status_code == 200
        assert second.status_code == 409


def test_login_rejects_wrong_password() -> None:
    with TemporaryDirectory() as temp_dir:
        client, _ = make_test_client(temp_dir)
        client.post(
            "/api/auth/register",
            json={"username": "tester_01", "password": "password123"},
        )

        response = client.post(
            "/api/auth/login",
            json={"username": "tester_01", "password": "wrong-pass"},
        )

        assert response.status_code == 401


def test_me_requires_valid_bearer_token() -> None:
    with TemporaryDirectory() as temp_dir:
        client, _ = make_test_client(temp_dir)
        auth_response = client.post(
            "/api/auth/register",
            json={"username": "tester_01", "password": "password123"},
        )
        token = auth_response.json()["access_token"]

        success = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        failure = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid-token"},
        )

        assert success.status_code == 200
        assert success.json()["user"]["username"] == "tester_01"
        assert failure.status_code == 401


def test_authenticated_progress_persists_after_restart() -> None:
    with TemporaryDirectory() as temp_dir:
        first_client, first_service = make_test_client(temp_dir)
        register_response = first_client.post(
            "/api/auth/register",
            json={"username": "tester_01", "password": "password123"},
        )
        token = register_response.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        start_response = first_client.post("/api/session/start-current-level", headers=headers)
        session = start_response.json()
        target_label = first_service.sessions[session["session_id"]].target.label
        guessed = first_client.post(
            f"/api/session/{session['session_id']}/guess",
            headers=headers,
            json={"label": target_label},
        )

        assert guessed.status_code == 200
        assert guessed.json()["awaiting_advancement"] is True

        advanced = first_client.post(
            f"/api/session/{session['session_id']}/advance",
            headers=headers,
        )
        assert advanced.status_code == 200

        second_client, _ = make_test_client(temp_dir)
        me_response = second_client.get("/api/auth/me", headers=headers)

        assert me_response.status_code == 200
        assert me_response.json()["progression"]["current_level_id"] == "chapter-1-level-2"
        assert me_response.json()["progression"]["campaign_total_score"] > 0


def test_leaderboard_sorts_by_total_score_then_completion() -> None:
    with TemporaryDirectory() as temp_dir:
        store = SQLiteAuthStore(Path(temp_dir) / "auth.sqlite3")
        alpha = store.create_user("alpha", "hash-a")
        bravo = store.create_user("bravo", "hash-b")
        charlie = store.create_user("charlie", "hash-c")

        store.save_progress(
            alpha.id,
            PlayerCampaignProgress(
                best_scores_by_level={"chapter-1-level-1": 120, "chapter-1-level-2": 80},
                completed_level_ids={"chapter-1-level-1", "chapter-1-level-2"},
            ),
        )
        store.save_progress(
            bravo.id,
            PlayerCampaignProgress(
                best_scores_by_level={"chapter-1-level-1": 200},
                completed_level_ids={"chapter-1-level-1"},
            ),
        )
        store.save_progress(
            charlie.id,
            PlayerCampaignProgress(
                best_scores_by_level={"chapter-1-level-1": 200, "chapter-1-level-2": 10},
                completed_level_ids={"chapter-1-level-1", "chapter-1-level-2"},
            ),
        )

        leaderboard = store.list_leaderboard()

        assert [entry.username for entry in leaderboard[:3]] == ["charlie", "alpha", "bravo"]
        assert leaderboard[0].campaign_total_score == 210
        assert leaderboard[1].campaign_total_score == 200
        assert leaderboard[1].completed_count == 2
        assert leaderboard[2].completed_count == 1


def test_leaderboard_returns_all_accounts_without_default_truncation() -> None:
    with TemporaryDirectory() as temp_dir:
        store = SQLiteAuthStore(Path(temp_dir) / "auth.sqlite3")

        for index in range(12):
            user = store.create_user(f"user_{index:02d}", f"hash-{index}")
            store.save_progress(
                user.id,
                PlayerCampaignProgress(
                    best_scores_by_level={"chapter-1-level-1": 12 - index},
                    completed_level_ids={"chapter-1-level-1"},
                ),
            )

        leaderboard = store.list_leaderboard()

        assert len(leaderboard) == 12
        assert leaderboard[0].username == "user_00"
        assert leaderboard[-1].username == "user_11"


def test_sqlite_store_migrates_old_progress_table() -> None:
    with TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "legacy.sqlite3"
        connection = sqlite3.connect(db_path)
        connection.executescript(
            """
            CREATE TABLE users (
                id TEXT PRIMARY KEY,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at INTEGER NOT NULL
            );

            CREATE TABLE campaign_progress (
                user_id TEXT PRIMARY KEY,
                current_level_id TEXT NOT NULL,
                highest_unlocked_level_id TEXT NOT NULL,
                completed_level_ids TEXT NOT NULL,
                streak INTEGER NOT NULL,
                campaign_complete INTEGER NOT NULL,
                updated_at INTEGER NOT NULL
            );
            """
        )
        connection.commit()
        connection.close()

        store = SQLiteAuthStore(db_path)
        with store._connect() as connection:
            columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(campaign_progress)").fetchall()
            }

        assert "best_scores_by_level" in columns
