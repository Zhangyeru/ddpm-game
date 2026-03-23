from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .schemas import FreezeRequest, GuessRequest, SessionSnapshot, UseCardRequest
from .service import GameService


app = FastAPI(
    title="Noise Archaeologist API",
    description="Mock gameplay backend for the DDPM web game prototype.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

service = GameService()


@app.get("/health")
def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/session/start", response_model=SessionSnapshot)
def start_session() -> SessionSnapshot:
    return service.start_session()


@app.post("/api/session/{session_id}/step", response_model=SessionSnapshot)
def step_session(session_id: str) -> SessionSnapshot:
    try:
        return service.step(session_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.post("/api/session/{session_id}/guess", response_model=SessionSnapshot)
def guess_session(session_id: str, payload: GuessRequest) -> SessionSnapshot:
    try:
        return service.guess(session_id, payload.label)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.post("/api/session/{session_id}/use-card", response_model=SessionSnapshot)
def use_card(session_id: str, payload: UseCardRequest) -> SessionSnapshot:
    try:
        return service.use_card(session_id, payload.card_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/api/session/{session_id}/freeze", response_model=SessionSnapshot)
def freeze_region(session_id: str, payload: FreezeRequest) -> SessionSnapshot:
    try:
        return service.freeze(session_id, payload.region)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
