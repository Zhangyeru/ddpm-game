from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.main import app, service


client = TestClient(app)


def test_frame_endpoint_returns_webp_image() -> None:
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
    headers = {"X-Player-Id": "api-progress-player"}

    progression_response = client.get("/api/progression", headers=headers)
    assert progression_response.status_code == 200
    assert progression_response.json()["current_level_id"] == "chapter-1-level-1"

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
