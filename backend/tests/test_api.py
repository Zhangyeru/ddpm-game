from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient

from backend.app.auth import actor_id_for_anonymous
from backend.app.main import create_app
from backend.app.settings import Settings


def make_test_client(temp_dir: str) -> tuple[TestClient, object]:
    app = create_app(
        Settings(
            db_path=Path(temp_dir) / "test.sqlite3",
            jwt_secret="test-secret",
            jwt_expires_seconds=3600,
        )
    )
    return TestClient(app), app.state.service


def test_frame_endpoint_returns_webp_image() -> None:
    with TemporaryDirectory() as temp_dir:
        client, _ = make_test_client(temp_dir)
        start_response = client.post("/api/session/start")
        assert start_response.status_code == 200

        snapshot = start_response.json()
        image_url = snapshot["image_url"]

        frame_response = client.get(image_url)

        assert frame_response.status_code == 200
        assert frame_response.headers["content-type"] == "image/webp"
        assert frame_response.content[:4] == b"RIFF"
        assert frame_response.content[8:12] == b"WEBP"


def test_progression_and_advance_endpoints_work() -> None:
    with TemporaryDirectory() as temp_dir:
        client, service = make_test_client(temp_dir)
        headers = {"X-Player-Id": "api-progress-player"}

        progression_response = client.get("/api/progression", headers=headers)
        assert progression_response.status_code == 200
        assert progression_response.json()["current_level_id"] == "chapter-1-level-1"
        assert progression_response.json()["campaign_total_score"] == 0

        start_response = client.post("/api/session/start-current-level", headers=headers)
        assert start_response.status_code == 200
        snapshot = start_response.json()
        target_label = service.sessions[snapshot["session_id"]].target.label

        guess_response = client.post(
            f"/api/session/{snapshot['session_id']}/guess",
            headers=headers,
            json={"label": target_label},
        )
        assert guess_response.status_code == 200
        assert guess_response.json()["awaiting_advancement"] is True

        advance_response = client.post(
            f"/api/session/{snapshot['session_id']}/advance",
            headers=headers,
        )
        assert advance_response.status_code == 200
        assert advance_response.json()["level_id"] == "chapter-1-level-2"

        refreshed_progression = client.get("/api/progression", headers=headers)
        assert refreshed_progression.status_code == 200
        assert refreshed_progression.json()["campaign_total_score"] > 0


def test_start_specific_level_endpoint_works() -> None:
    with TemporaryDirectory() as temp_dir:
        client, _ = make_test_client(temp_dir)
        headers = {"X-Player-Id": "api-start-level-player"}

        response = client.post("/api/session/start-level/chapter-3-level-2", headers=headers)

        assert response.status_code == 200
        assert response.json()["level_id"] == "chapter-3-level-2"
        assert response.json()["level_title"] == "连推风险"


def test_commit_family_and_freeze_endpoints_work() -> None:
    with TemporaryDirectory() as temp_dir:
        client, service = make_test_client(temp_dir)
        headers = {"X-Player-Id": "api-rule-player"}
        actor_id = actor_id_for_anonymous("api-rule-player")

        progress = service._campaign_progress(actor_id)
        progress.current_level_id = "chapter-3-level-1"

        classify_session = client.post("/api/session/start-current-level", headers=headers).json()
        target_family = service.sessions[classify_session["session_id"]].target.family
        commit_response = client.post(
            f"/api/session/{classify_session['session_id']}/commit-family",
            headers=headers,
            json={"family": target_family},
        )

        assert commit_response.status_code == 200
        assert commit_response.json()["committed_family"] == target_family
        assert commit_response.json()["objective_phase"] == "identify"

        progress.current_level_id = "chapter-1-level-3"

        freeze_session = client.post("/api/session/start-current-level", headers=headers).json()
        freeze_response = client.post(
            f"/api/session/{freeze_session['session_id']}/freeze",
            headers=headers,
            json={"region": "center"},
        )

        assert freeze_response.status_code == 200
        assert freeze_response.json()["frozen_region"] == "center"
        assert freeze_response.json()["freeze_remaining"] == 0


def test_leaderboard_endpoint_returns_ranked_users() -> None:
    with TemporaryDirectory() as temp_dir:
        client, service = make_test_client(temp_dir)

        alpha = client.post(
            "/api/auth/register",
            json={"username": "alpha", "password": "password123"},
        )
        bravo = client.post(
            "/api/auth/register",
            json={"username": "bravo", "password": "password123"},
        )
        alpha_headers = {"Authorization": f"Bearer {alpha.json()['access_token']}"}
        bravo_headers = {"Authorization": f"Bearer {bravo.json()['access_token']}"}

        alpha_session = client.post("/api/session/start-current-level", headers=alpha_headers).json()
        alpha_target = service.sessions[alpha_session["session_id"]].target.label
        client.post(
            f"/api/session/{alpha_session['session_id']}/guess",
            headers=alpha_headers,
            json={"label": alpha_target},
        )

        leaderboard_response = client.get("/api/leaderboard")

        assert leaderboard_response.status_code == 200
        payload = leaderboard_response.json()
        assert payload[0]["rank"] == 1
        assert payload[0]["username"] == "alpha"
        assert payload[0]["campaign_total_score"] > 0
        assert payload[1]["username"] == "bravo"
