from __future__ import annotations

from fastapi.testclient import TestClient

from backend.app.main import app


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
