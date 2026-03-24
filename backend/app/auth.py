from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import sqlite3
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from threading import RLock

from .gameplay_config import first_level


USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_]{3,20}$")
JWT_ALGORITHM = "HS256"


class AuthError(Exception):
    pass


class AuthenticationError(AuthError):
    pass


class DuplicateUsernameError(AuthError):
    pass


@dataclass(frozen=True)
class AuthUserRecord:
    id: str
    username: str


@dataclass(frozen=True)
class LeaderboardRecord:
    rank: int
    user_id: str
    username: str
    campaign_total_score: int
    completed_count: int
    campaign_complete: bool


@dataclass
class PlayerCampaignProgress:
    current_level_id: str = field(default_factory=lambda: first_level().level_id)
    highest_unlocked_level_id: str = field(default_factory=lambda: first_level().level_id)
    completed_level_ids: set[str] = field(default_factory=set)
    best_scores_by_level: dict[str, int] = field(default_factory=dict)
    streak: int = 0
    campaign_complete: bool = False


def actor_id_for_user(user_id: str) -> str:
    return f"user:{user_id}"


def actor_id_for_anonymous(player_id: str | None) -> str:
    normalized = normalize_anonymous_player_id(player_id)
    return f"anon:{normalized}"


def is_user_actor(actor_id: str) -> bool:
    return actor_id.startswith("user:")


def user_id_from_actor(actor_id: str) -> str:
    if not is_user_actor(actor_id):
        raise ValueError("当前 actor 不是登录用户。")
    return actor_id.split(":", 1)[1]


def normalize_anonymous_player_id(player_id: str | None) -> str:
    if player_id is None:
        return "anonymous"
    normalized = player_id.strip()
    if not normalized:
        return "anonymous"
    return normalized[:64]


class SQLiteAuthStore:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._lock = RLock()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def create_user(self, username: str, password_hash: str) -> AuthUserRecord:
        with self._lock, self._connect() as connection:
            user_id = uuid.uuid4().hex
            try:
                connection.execute(
                    """
                    INSERT INTO users (id, username, password_hash, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (user_id, username, password_hash, int(time.time())),
                )
            except sqlite3.IntegrityError as error:
                raise DuplicateUsernameError("用户名已存在。") from error

            self._upsert_progress(connection, user_id, PlayerCampaignProgress())
            connection.commit()
            return AuthUserRecord(id=user_id, username=username)

    def get_user_by_username(self, username: str) -> AuthUserRecord | None:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT id, username FROM users WHERE username = ?",
                (username,),
            ).fetchone()
        return self._row_to_user(row)

    def get_user_password_hash(self, username: str) -> str | None:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT password_hash FROM users WHERE username = ?",
                (username,),
            ).fetchone()
        if row is None:
            return None
        return str(row["password_hash"])

    def get_user_by_id(self, user_id: str) -> AuthUserRecord | None:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                "SELECT id, username FROM users WHERE id = ?",
                (user_id,),
            ).fetchone()
        return self._row_to_user(row)

    def get_or_create_progress(self, user_id: str) -> PlayerCampaignProgress:
        with self._lock, self._connect() as connection:
            row = connection.execute(
                """
                SELECT current_level_id, highest_unlocked_level_id, completed_level_ids,
                       best_scores_by_level, streak, campaign_complete
                FROM campaign_progress
                WHERE user_id = ?
                """,
                (user_id,),
            ).fetchone()
            if row is None:
                progress = PlayerCampaignProgress()
                self._upsert_progress(connection, user_id, progress)
                connection.commit()
                return progress
            return self._row_to_progress(row)

    def save_progress(self, user_id: str, progress: PlayerCampaignProgress) -> None:
        with self._lock, self._connect() as connection:
            self._upsert_progress(connection, user_id, progress)
            connection.commit()

    def list_leaderboard(self, *, limit: int | None = None) -> list[LeaderboardRecord]:
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                """
                SELECT users.id, users.username,
                       campaign_progress.completed_level_ids,
                       campaign_progress.best_scores_by_level,
                       campaign_progress.campaign_complete
                FROM users
                INNER JOIN campaign_progress ON campaign_progress.user_id = users.id
                """
            ).fetchall()

        records: list[tuple[str, str, int, int, bool]] = []
        for row in rows:
            completed_ids = json.loads(str(row["completed_level_ids"]))
            raw_scores = json.loads(str(row["best_scores_by_level"]))
            if not isinstance(raw_scores, dict):
                raw_scores = {}
            total_score = sum(int(score) for score in raw_scores.values())
            records.append(
                (
                    str(row["id"]),
                    str(row["username"]),
                    total_score,
                    len(list(completed_ids)),
                    bool(row["campaign_complete"]),
                )
            )

        records.sort(key=lambda item: (-item[2], -item[3], item[1].lower()))
        visible_records = records if limit is None else records[: max(1, min(limit, 200))]
        return [
            LeaderboardRecord(
                rank=index + 1,
                user_id=user_id,
                username=username,
                campaign_total_score=campaign_total_score,
                completed_count=completed_count,
                campaign_complete=campaign_complete,
            )
            for index, (user_id, username, campaign_total_score, completed_count, campaign_complete) in enumerate(visible_records)
        ]

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._lock, self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    created_at INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS campaign_progress (
                    user_id TEXT PRIMARY KEY,
                    current_level_id TEXT NOT NULL,
                    highest_unlocked_level_id TEXT NOT NULL,
                    completed_level_ids TEXT NOT NULL,
                    best_scores_by_level TEXT NOT NULL DEFAULT '{}',
                    streak INTEGER NOT NULL,
                    campaign_complete INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
                );
                """
            )
            columns = {
                str(row["name"])
                for row in connection.execute("PRAGMA table_info(campaign_progress)").fetchall()
            }
            if "best_scores_by_level" not in columns:
                connection.execute(
                    """
                    ALTER TABLE campaign_progress
                    ADD COLUMN best_scores_by_level TEXT NOT NULL DEFAULT '{}'
                    """
                )
            connection.commit()

    def _upsert_progress(
        self,
        connection: sqlite3.Connection,
        user_id: str,
        progress: PlayerCampaignProgress,
    ) -> None:
        connection.execute(
            """
            INSERT INTO campaign_progress (
                user_id,
                current_level_id,
                highest_unlocked_level_id,
                completed_level_ids,
                best_scores_by_level,
                streak,
                campaign_complete,
                updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                current_level_id = excluded.current_level_id,
                highest_unlocked_level_id = excluded.highest_unlocked_level_id,
                completed_level_ids = excluded.completed_level_ids,
                best_scores_by_level = excluded.best_scores_by_level,
                streak = excluded.streak,
                campaign_complete = excluded.campaign_complete,
                updated_at = excluded.updated_at
            """,
            (
                user_id,
                progress.current_level_id,
                progress.highest_unlocked_level_id,
                json.dumps(sorted(progress.completed_level_ids), ensure_ascii=False),
                json.dumps(progress.best_scores_by_level, ensure_ascii=False, sort_keys=True),
                progress.streak,
                1 if progress.campaign_complete else 0,
                int(time.time()),
            ),
        )

    def _row_to_user(self, row: sqlite3.Row | None) -> AuthUserRecord | None:
        if row is None:
            return None
        return AuthUserRecord(
            id=str(row["id"]),
            username=str(row["username"]),
        )

    def _row_to_progress(self, row: sqlite3.Row) -> PlayerCampaignProgress:
        completed_raw = row["completed_level_ids"]
        completed_level_ids = set(json.loads(str(completed_raw)))
        score_map_raw = row["best_scores_by_level"]
        parsed_score_map = json.loads(str(score_map_raw))
        if not isinstance(parsed_score_map, dict):
            parsed_score_map = {}
        best_scores_by_level = {
            str(level_id): int(score)
            for level_id, score in parsed_score_map.items()
        }
        return PlayerCampaignProgress(
            current_level_id=str(row["current_level_id"]),
            highest_unlocked_level_id=str(row["highest_unlocked_level_id"]),
            completed_level_ids=completed_level_ids,
            best_scores_by_level=best_scores_by_level,
            streak=int(row["streak"]),
            campaign_complete=bool(row["campaign_complete"]),
        )


class AuthService:
    def __init__(
        self,
        store: SQLiteAuthStore,
        *,
        jwt_secret: str,
        jwt_expires_seconds: int,
    ) -> None:
        self.store = store
        self.jwt_secret = jwt_secret
        self.jwt_expires_seconds = jwt_expires_seconds

    def register(self, username: str, password: str) -> tuple[AuthUserRecord, str]:
        normalized_username = self._validate_username(username)
        self._validate_password(password)
        user = self.store.create_user(
            normalized_username,
            self._hash_password(password),
        )
        return user, self.issue_token(user)

    def login(self, username: str, password: str) -> tuple[AuthUserRecord, str]:
        normalized_username = username.strip()
        password_hash = self.store.get_user_password_hash(normalized_username)
        user = self.store.get_user_by_username(normalized_username)
        if user is None or password_hash is None or not self._verify_password(password, password_hash):
            raise AuthenticationError("用户名或密码错误。")
        return user, self.issue_token(user)

    def authenticate_bearer_header(self, authorization: str | None) -> AuthUserRecord:
        if authorization is None:
            raise AuthenticationError("缺少登录凭证。")
        scheme, _, token = authorization.partition(" ")
        if scheme.lower() != "bearer" or not token.strip():
            raise AuthenticationError("登录凭证格式无效。")
        return self.authenticate_token(token.strip())

    def authenticate_token(self, token: str) -> AuthUserRecord:
        try:
            header_segment, payload_segment, signature_segment = token.split(".")
        except ValueError as error:
            raise AuthenticationError("登录凭证格式无效。") from error

        signing_input = f"{header_segment}.{payload_segment}".encode("utf-8")
        expected_signature = self._sign(signing_input)
        if not hmac.compare_digest(expected_signature, signature_segment):
            raise AuthenticationError("登录凭证无效。")

        try:
            header = json.loads(self._base64url_decode(header_segment))
            payload = json.loads(self._base64url_decode(payload_segment))
        except (ValueError, json.JSONDecodeError) as error:
            raise AuthenticationError("登录凭证格式无效。") from error

        if header.get("alg") != JWT_ALGORITHM or header.get("typ") != "JWT":
            raise AuthenticationError("登录凭证格式无效。")

        exp = payload.get("exp")
        subject = payload.get("sub")
        if not isinstance(exp, int) or not isinstance(subject, str):
            raise AuthenticationError("登录凭证格式无效。")
        if exp < int(time.time()):
            raise AuthenticationError("登录凭证已过期。")

        user = self.store.get_user_by_id(subject)
        if user is None:
            raise AuthenticationError("当前账号不存在。")
        return user

    def issue_token(self, user: AuthUserRecord) -> str:
        issued_at = int(time.time())
        header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
        payload = {
            "sub": user.id,
            "username": user.username,
            "iat": issued_at,
            "exp": issued_at + self.jwt_expires_seconds,
        }
        header_segment = self._base64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
        payload_segment = self._base64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        signing_input = f"{header_segment}.{payload_segment}".encode("utf-8")
        signature_segment = self._sign(signing_input)
        return f"{header_segment}.{payload_segment}.{signature_segment}"

    def _validate_username(self, username: str) -> str:
        normalized = username.strip()
        if not USERNAME_PATTERN.fullmatch(normalized):
            raise ValueError("用户名需为 3-20 位，仅可包含字母、数字和下划线。")
        return normalized

    def _validate_password(self, password: str) -> None:
        if len(password) < 8:
            raise ValueError("密码至少需要 8 位。")

    def _hash_password(self, password: str) -> str:
        salt = os.urandom(16)
        derived_key = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=2**14,
            r=8,
            p=1,
        )
        return (
            "scrypt$16384$8$1$"
            f"{self._base64url_encode(salt)}$"
            f"{self._base64url_encode(derived_key)}"
        )

    def _verify_password(self, password: str, stored_hash: str) -> bool:
        try:
            _, n_value, r_value, p_value, salt_segment, hash_segment = stored_hash.split("$")
            salt = self._base64url_decode_bytes(salt_segment)
            expected = self._base64url_decode_bytes(hash_segment)
            candidate = hashlib.scrypt(
                password.encode("utf-8"),
                salt=salt,
                n=int(n_value),
                r=int(r_value),
                p=int(p_value),
            )
            return hmac.compare_digest(candidate, expected)
        except (ValueError, TypeError):
            return False

    def _sign(self, signing_input: bytes) -> str:
        return self._base64url_encode(
            hmac.new(
                self.jwt_secret.encode("utf-8"),
                signing_input,
                hashlib.sha256,
            ).digest()
        )

    def _base64url_encode(self, value: bytes) -> str:
        return base64.urlsafe_b64encode(value).rstrip(b"=").decode("utf-8")

    def _base64url_decode(self, value: str) -> str:
        return self._base64url_decode_bytes(value).decode("utf-8")

    def _base64url_decode_bytes(self, value: str) -> bytes:
        padding = "=" * (-len(value) % 4)
        return base64.urlsafe_b64decode(f"{value}{padding}".encode("utf-8"))
