import base64
import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta, timezone
from typing import Any
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError

from src.core.config import get_settings

# Initialize Argon2id password hasher (OWASP recommended parameters)
_password_hasher = PasswordHasher(
    time_cost=2,
    memory_cost=65536,  # 64 MB
    parallelism=1,
    hash_len=32,
    salt_len=16,
)


class SecurityError(Exception):
    """Base exception for authentication and token validation errors."""
    pass


class InvalidTokenError(SecurityError):
    """Raised when a token signature is invalid, malformed, or missing required claims."""
    pass


class TokenExpiredError(SecurityError):
    """Raised when a token has expired."""
    pass


def hash_password(password: str) -> str:
    """Hashes a plaintext password using Argon2id with random salt."""
    if not password:
        raise ValueError("Password cannot be empty.")
    return _password_hasher.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plaintext password against an Argon2id hash in constant time."""
    if not plain_password or not hashed_password:
        return False
    try:
        return _password_hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, VerificationError):
        return False


def _b64encode(data: bytes) -> str:
    """Base64url encode without padding according to RFC 7515."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _b64decode(data: str) -> bytes:
    """Base64url decode with automatic padding calculation."""
    padding = "=" * (4 - (len(data) % 4)) if (len(data) % 4) != 0 else ""
    return base64.urlsafe_b64decode(data + padding)


def create_access_token(
    subject: str,
    role: str,
    crew_member_id: str | None = None,
    assigned_crew_ids: list[str] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Encodes a standard RFC 7519 JWT access token signed with HMAC-SHA256."""
    settings = get_settings()
    now_ts = int(datetime.now(timezone.utc).timestamp())
    exp_delta = expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    exp_ts = int((datetime.now(timezone.utc) + exp_delta).timestamp())

    header = {
        "alg": "HS256",
        "typ": "JWT",
    }
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
        "iat": now_ts,
        "exp": exp_ts,
    }
    if crew_member_id:
        payload["crew_member_id"] = crew_member_id
    if assigned_crew_ids:
        payload["assigned_crew_ids"] = assigned_crew_ids

    header_bytes = json.dumps(header, separators=(",", ":")).encode("utf-8")
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")

    signing_input = f"{_b64encode(header_bytes)}.{_b64encode(payload_bytes)}"
    signature = hmac.new(
        key=settings.SECRET_KEY.encode("utf-8"),
        msg=signing_input.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()

    return f"{signing_input}.{_b64encode(signature)}"


def decode_access_token(token: str) -> dict[str, Any]:
    """Validates and decodes a JWT access token.
    
    Verifies:
      - Valid three-part compact serialization
      - Algorithm HS256
      - HMAC-SHA256 cryptographic signature
      - Token expiration (exp)
      - Expected Issuer (iss)
      - Expected Audience (aud)
      - Subject and role presence
    """
    settings = get_settings()
    if not token or not isinstance(token, str):
        raise InvalidTokenError("Missing or invalid token format.")

    parts = token.strip().split(".")
    if len(parts) != 3:
        raise InvalidTokenError("Malformed token structure: must contain header, payload, and signature.")

    header_b64, payload_b64, signature_b64 = parts

    # 1. Verify Signature
    signing_input = f"{header_b64}.{payload_b64}"
    expected_signature = hmac.new(
        key=settings.SECRET_KEY.encode("utf-8"),
        msg=signing_input.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()

    try:
        provided_signature = _b64decode(signature_b64)
    except Exception:
        raise InvalidTokenError("Malformed token signature encoding.")

    if not hmac.compare_digest(expected_signature, provided_signature):
        raise InvalidTokenError("Invalid token signature.")

    # 2. Decode Header
    try:
        header = json.loads(_b64decode(header_b64).decode("utf-8"))
        if header.get("alg") != "HS256":
            raise InvalidTokenError(f"Unsupported token algorithm: '{header.get('alg')}'.")
    except Exception as exc:
        if isinstance(exc, InvalidTokenError):
            raise
        raise InvalidTokenError("Malformed token header.")

    # 3. Decode Payload
    try:
        payload = json.loads(_b64decode(payload_b64).decode("utf-8"))
    except Exception:
        raise InvalidTokenError("Malformed token payload.")

    # 4. Validate Claims
    now_ts = int(time.time())

    # Expiry
    exp = payload.get("exp")
    if exp is None:
        raise InvalidTokenError("Token missing expiration claim 'exp'.")
    if not isinstance(exp, (int, float)):
        raise InvalidTokenError("Invalid expiration claim type.")
    if now_ts >= exp:
        raise TokenExpiredError("Token has expired.")

    # Issuer
    iss = payload.get("iss")
    if iss != settings.JWT_ISSUER:
        raise InvalidTokenError(f"Token issuer '{iss}' does not match expected '{settings.JWT_ISSUER}'.")

    # Audience
    aud = payload.get("aud")
    if aud != settings.JWT_AUDIENCE:
        raise InvalidTokenError(f"Token audience '{aud}' does not match expected '{settings.JWT_AUDIENCE}'.")

    # Subject & Role
    if not payload.get("sub"):
        raise InvalidTokenError("Token missing subject 'sub' claim.")
    if not payload.get("role"):
        raise InvalidTokenError("Token missing 'role' claim.")

    return payload
