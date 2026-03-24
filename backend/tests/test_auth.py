from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

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
