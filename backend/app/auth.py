import os
import time
import json
import hmac
import base64
import hashlib
import sqlite3
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator
from fastapi import APIRouter, HTTPException, Header, status

# JWT Secret configuration
JWT_SECRET = os.getenv("JWT_SECRET", "truthlens_ai_super_secret_jwt_key_2026_production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_SECONDS = 7 * 24 * 3600  # 7 days

# SQLite DB Path
DB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data"))
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, "truthlens_auth.db")


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_auth_db():
    """Create users table and pre-seed demo account if not existing."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL COLLATE NOCASE,
                name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'Fact-Checker',
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()

        # Check demo user
        cursor.execute("SELECT id FROM users WHERE email = 'demo@truthlens.ai'")
        if not cursor.fetchone():
            salt, pw_hash = hash_password("truthlens123")
            created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            cursor.execute(
                """
                INSERT INTO users (email, name, password_hash, salt, role, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                ("demo@truthlens.ai", "Demo Investigator", pw_hash, salt, "Senior Fact-Checker", created_at),
            )
            conn.commit()


def hash_password(password: str) -> tuple[str, str]:
    """Secure PBKDF2-HMAC-SHA256 password hasher with 100,000 iterations."""
    salt = os.urandom(16).hex()
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return salt, key.hex()


def verify_password(password: str, stored_hash: str, salt: str) -> bool:
    """Verify password against stored salt and PBKDF2 hash."""
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return hmac.compare_digest(key.hex(), stored_hash)


def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def base64url_decode(data: str) -> bytes:
    padding = "=" * (4 - (len(data) % 4)) if (len(data) % 4) != 0 else ""
    return base64.urlsafe_b64decode((data + padding).encode("utf-8"))


def create_access_token(payload_data: Dict[str, Any]) -> str:
    """Generate signed HMAC-SHA256 JWT string without third-party dependencies."""
    header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
    payload = {
        **payload_data,
        "exp": int(time.time()) + JWT_EXPIRATION_SECONDS,
        "iat": int(time.time()),
    }
    encoded_header = base64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    encoded_payload = base64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{encoded_header}.{encoded_payload}".encode("utf-8")
    signature = hmac.new(JWT_SECRET.encode("utf-8"), signing_input, hashlib.sha256).digest()
    encoded_signature = base64url_encode(signature)
    return f"{encoded_header}.{encoded_payload}.{encoded_signature}"


def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify and parse JWT token."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        encoded_header, encoded_payload, encoded_signature = parts
        signing_input = f"{encoded_header}.{encoded_payload}".encode("utf-8")
        expected_sig = hmac.new(JWT_SECRET.encode("utf-8"), signing_input, hashlib.sha256).digest()
        actual_sig = base64url_decode(encoded_signature)
        if not hmac.compare_digest(expected_sig, actual_sig):
            return None
        payload = json.loads(base64url_decode(encoded_payload).decode("utf-8"))
        if payload.get("exp", 0) < int(time.time()):
            return None
        return payload
    except Exception:
        return None


# Schemas
class SignupRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=60)
    email: str = Field(..., min_length=5, max_length=120)
    password: str = Field(..., min_length=6, max_length=128)
    role: Optional[str] = "Fact-Checker"

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        clean = v.strip().lower()
        if "@" not in clean or "." not in clean.split("@")[-1]:
            raise ValueError("Please provide a valid email address.")
        return clean


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3)
    password: str = Field(..., min_length=1)

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        return v.strip().lower()


class UserProfile(BaseModel):
    id: int
    name: str
    email: str
    role: str
    created_at: str


class AuthResponse(BaseModel):
    status: str = "success"
    message: str
    access_token: str
    token_type: str = "bearer"
    user: UserProfile


# Router
auth_router = APIRouter(prefix="/v2/auth", tags=["Authentication"])


@auth_router.post("/signup", response_model=AuthResponse)
def signup(payload: SignupRequest):
    clean_email = payload.email.strip().lower()
    clean_name = payload.name.strip()

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE email = ?", (clean_email,))
        if cursor.fetchone():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="An account with this email address already exists. Please sign in instead.",
            )

        salt, pw_hash = hash_password(payload.password)
        created_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        cursor.execute(
            """
            INSERT INTO users (email, name, password_hash, salt, role, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (clean_email, clean_name, pw_hash, salt, payload.role or "Fact-Checker", created_at),
        )
        conn.commit()
        user_id = cursor.lastrowid

    user_data = {
        "id": user_id,
        "name": clean_name,
        "email": clean_email,
        "role": payload.role or "Fact-Checker",
        "created_at": created_at,
    }
    token = create_access_token(user_data)
    return AuthResponse(
        message="Account created successfully! Welcome to TruthLens AI.",
        access_token=token,
        user=UserProfile(**user_data),
    )


@auth_router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest):
    clean_email = payload.email.strip().lower()

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, email, password_hash, salt, role, created_at FROM users WHERE email = ?",
            (clean_email,),
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password. Please verify your credentials.",
            )

        if not verify_password(payload.password, row["password_hash"], row["salt"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password. Please verify your credentials.",
            )

        user_data = {
            "id": row["id"],
            "name": row["name"],
            "email": row["email"],
            "role": row["role"],
            "created_at": row["created_at"],
        }

    token = create_access_token(user_data)
    return AuthResponse(
        message="Signed in successfully. Welcome back!",
        access_token=token,
        user=UserProfile(**user_data),
    )


@auth_router.post("/demo", response_model=AuthResponse)
def demo_login():
    """Instant 1-Click login for evaluators, professors, and reviewers."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, email, role, created_at FROM users WHERE email = 'demo@truthlens.ai'"
        )
        row = cursor.fetchone()
        if not row:
            init_auth_db()
            cursor.execute(
                "SELECT id, name, email, role, created_at FROM users WHERE email = 'demo@truthlens.ai'"
            )
            row = cursor.fetchone()

        user_data = {
            "id": row["id"],
            "name": row["name"],
            "email": row["email"],
            "role": row["role"],
            "created_at": row["created_at"],
        }

    token = create_access_token(user_data)
    return AuthResponse(
        message="Welcome Demo Investigator! You now have full cloud verification access.",
        access_token=token,
        user=UserProfile(**user_data),
    )


@auth_router.get("/me", response_model=Dict[str, Any])
def get_current_user(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header.",
        )

    token = authorization.split(" ")[1]
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid. Please sign in again.",
        )

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, name, email, role, created_at FROM users WHERE id = ?",
            (payload.get("id"),),
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User account no longer exists.",
            )

        return {
            "status": "authenticated",
            "user": {
                "id": row["id"],
                "name": row["name"],
                "email": row["email"],
                "role": row["role"],
                "created_at": row["created_at"],
            },
        }
