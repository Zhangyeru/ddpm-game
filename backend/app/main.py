from __future__ import annotations

from fastapi import FastAPI, Header, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware

from .auth import (
    AuthenticationError,
    AuthService,
    DuplicateUsernameError,
    SQLiteAuthStore,
    actor_id_for_anonymous,
    actor_id_for_user,
)
from .schemas import (
    AuthResponse,
    AuthSessionSnapshot,
    AuthUser,
    GuessRequest,
    LeaderboardEntry,
    LoginRequest,
    ProgressSnapshot,
    RegisterRequest,
    SessionSnapshot,
    UseCardRequest,
)
from .service import GameService
from .settings import Settings, load_settings
from .trajectory_store import TrajectoryStore


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings or load_settings()
    trajectory_store = (
        TrajectoryStore(resolved_settings.trajectory_manifest_path)
        if resolved_settings.trajectory_manifest_path is not None
        else TrajectoryStore()
    )
    auth_store = SQLiteAuthStore(resolved_settings.db_path)
    auth_service = AuthService(
        auth_store,
        jwt_secret=resolved_settings.jwt_secret,
        jwt_expires_seconds=resolved_settings.jwt_expires_seconds,
    )
    game_service = GameService(
        trajectory_store=trajectory_store,
        auth_store=auth_store,
    )

    app = FastAPI(
        title="Noise Archaeologist API",
        description="Mock gameplay backend for the DDPM web game prototype.",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(resolved_settings.allowed_origins),
        allow_origin_regex=resolved_settings.allowed_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.settings = resolved_settings
    app.state.service = game_service
    app.state.auth_service = auth_service

    def resolve_actor_id(
        authorization: str | None,
        player_id: str | None,
    ) -> str:
        if authorization and authorization.strip():
            user = auth_service.authenticate_bearer_header(authorization)
            return actor_id_for_user(user.id)
        return actor_id_for_anonymous(player_id)

    def auth_user_model(user_id: str, username: str) -> AuthUser:
        return AuthUser(id=user_id, username=username)

    @app.get("/health")
    def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/auth/register", response_model=AuthResponse)
    def register(payload: RegisterRequest) -> AuthResponse:
        try:
            user, token = auth_service.register(payload.username, payload.password)
        except DuplicateUsernameError as error:
            raise HTTPException(status_code=409, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

        progression = game_service.get_progression(actor_id_for_user(user.id))
        return AuthResponse(
            access_token=token,
            token_type="bearer",
            user=auth_user_model(user.id, user.username),
            progression=progression,
        )

    @app.post("/api/auth/login", response_model=AuthResponse)
    def login(payload: LoginRequest) -> AuthResponse:
        try:
            user, token = auth_service.login(payload.username, payload.password)
        except AuthenticationError as error:
            raise HTTPException(status_code=401, detail=str(error)) from error

        progression = game_service.get_progression(actor_id_for_user(user.id))
        return AuthResponse(
            access_token=token,
            token_type="bearer",
            user=auth_user_model(user.id, user.username),
            progression=progression,
        )

    @app.get("/api/auth/me", response_model=AuthSessionSnapshot)
    def auth_me(authorization: str | None = Header(default=None, alias="Authorization")) -> AuthSessionSnapshot:
        try:
            user = auth_service.authenticate_bearer_header(authorization)
        except AuthenticationError as error:
            raise HTTPException(status_code=401, detail=str(error)) from error

        progression = game_service.get_progression(actor_id_for_user(user.id))
        return AuthSessionSnapshot(
            user=auth_user_model(user.id, user.username),
            progression=progression,
        )

    @app.get("/api/leaderboard", response_model=list[LeaderboardEntry])
    def leaderboard() -> list[LeaderboardEntry]:
        records = auth_store.list_leaderboard()
        return [
            LeaderboardEntry(
                rank=record.rank,
                user_id=record.user_id,
                username=record.username,
                campaign_total_score=record.campaign_total_score,
                completed_count=record.completed_count,
                campaign_complete=record.campaign_complete,
            )
            for record in records
        ]

    @app.post("/api/session/start", response_model=SessionSnapshot)
    def start_session(
        player_id: str | None = Header(default=None, alias="X-Player-Id"),
        authorization: str | None = Header(default=None, alias="Authorization"),
    ) -> SessionSnapshot:
        try:
            actor_id = resolve_actor_id(authorization, player_id)
            return game_service.start_current_level(actor_id)
        except AuthenticationError as error:
            raise HTTPException(status_code=401, detail=str(error)) from error

    @app.post("/api/session/start-current-level", response_model=SessionSnapshot)
    def start_current_level(
        player_id: str | None = Header(default=None, alias="X-Player-Id"),
        authorization: str | None = Header(default=None, alias="Authorization"),
    ) -> SessionSnapshot:
        try:
            actor_id = resolve_actor_id(authorization, player_id)
            return game_service.start_current_level(actor_id)
        except AuthenticationError as error:
            raise HTTPException(status_code=401, detail=str(error)) from error

    @app.get("/api/progression", response_model=ProgressSnapshot)
    def get_progression(
        player_id: str | None = Header(default=None, alias="X-Player-Id"),
        authorization: str | None = Header(default=None, alias="Authorization"),
    ) -> ProgressSnapshot:
        try:
            actor_id = resolve_actor_id(authorization, player_id)
            return game_service.get_progression(actor_id)
        except AuthenticationError as error:
            raise HTTPException(status_code=401, detail=str(error)) from error

    @app.post("/api/session/{session_id}/step", response_model=SessionSnapshot)
    def step_session(
        session_id: str,
        player_id: str | None = Header(default=None, alias="X-Player-Id"),
        authorization: str | None = Header(default=None, alias="Authorization"),
    ) -> SessionSnapshot:
        try:
            actor_id = resolve_actor_id(authorization, player_id)
            return game_service.step(actor_id, session_id)
        except AuthenticationError as error:
            raise HTTPException(status_code=401, detail=str(error)) from error
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error

    @app.post("/api/session/{session_id}/guess", response_model=SessionSnapshot)
    def guess_session(
        session_id: str,
        payload: GuessRequest,
        player_id: str | None = Header(default=None, alias="X-Player-Id"),
        authorization: str | None = Header(default=None, alias="Authorization"),
    ) -> SessionSnapshot:
        try:
            actor_id = resolve_actor_id(authorization, player_id)
            return game_service.guess(actor_id, session_id, payload.label)
        except AuthenticationError as error:
            raise HTTPException(status_code=401, detail=str(error)) from error
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

    @app.post("/api/session/{session_id}/use-card", response_model=SessionSnapshot)
    def use_card(
        session_id: str,
        payload: UseCardRequest,
        player_id: str | None = Header(default=None, alias="X-Player-Id"),
        authorization: str | None = Header(default=None, alias="Authorization"),
    ) -> SessionSnapshot:
        try:
            actor_id = resolve_actor_id(authorization, player_id)
            return game_service.use_card(actor_id, session_id, payload.card_id)
        except AuthenticationError as error:
            raise HTTPException(status_code=401, detail=str(error)) from error
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

    @app.post("/api/session/{session_id}/advance", response_model=SessionSnapshot)
    def advance_session(
        session_id: str,
        player_id: str | None = Header(default=None, alias="X-Player-Id"),
        authorization: str | None = Header(default=None, alias="Authorization"),
    ) -> SessionSnapshot:
        try:
            actor_id = resolve_actor_id(authorization, player_id)
            return game_service.advance(actor_id, session_id)
        except AuthenticationError as error:
            raise HTTPException(status_code=401, detail=str(error)) from error
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

    @app.get("/api/session/{session_id}/frames/{frame_index}")
    def session_frame(session_id: str, frame_index: int, variant: str, token: str) -> Response:
        try:
            asset = game_service.render_frame(session_id, frame_index, variant, token)
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

    return app


settings = load_settings()
app = create_app(settings)
service = app.state.service
auth_service = app.state.auth_service
