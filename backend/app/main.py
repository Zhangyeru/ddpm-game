from __future__ import annotations

from fastapi import FastAPI, Header, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware

from .schemas import GuessRequest, SessionSnapshot, UseCardRequest
from .service import GameService
from .settings import load_settings
from .trajectory_store import TrajectoryStore


settings = load_settings()
trajectory_store = (
    TrajectoryStore(settings.trajectory_manifest_path)
    if settings.trajectory_manifest_path is not None
    else TrajectoryStore()
)


app = FastAPI(
    title="Noise Archaeologist API",
    description="Mock gameplay backend for the DDPM web game prototype.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_origin_regex=settings.allowed_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

service = GameService(trajectory_store=trajectory_store)


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/session/start", response_model=SessionSnapshot)
def start_session(player_id: str | None = Header(default=None, alias="X-Player-Id")) -> SessionSnapshot:
    return service.start_session(player_id)


@app.post("/api/session/{session_id}/step", response_model=SessionSnapshot)
def step_session(
    session_id: str,
    player_id: str | None = Header(default=None, alias="X-Player-Id"),
) -> SessionSnapshot:
    try:
        return service.step(player_id, session_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.post("/api/session/{session_id}/guess", response_model=SessionSnapshot)
def guess_session(
    session_id: str,
    payload: GuessRequest,
    player_id: str | None = Header(default=None, alias="X-Player-Id"),
) -> SessionSnapshot:
    try:
        return service.guess(player_id, session_id, payload.label)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/api/session/{session_id}/use-card", response_model=SessionSnapshot)
def use_card(
    session_id: str,
    payload: UseCardRequest,
    player_id: str | None = Header(default=None, alias="X-Player-Id"),
) -> SessionSnapshot:
    try:
        return service.use_card(player_id, session_id, payload.card_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.get("/api/session/{session_id}/frames/{frame_index}")
def session_frame(session_id: str, frame_index: int, variant: str, token: str) -> Response:
    try:
        asset = service.render_frame(session_id, frame_index, variant, token)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except PermissionError as error:
        raise HTTPException(status_code=403, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error

    return Response(
        content=asset.read_bytes(),
        media_type=asset.media_type,
        headers={"Cache-Control": "public, max-age=86400, immutable"},
    )
