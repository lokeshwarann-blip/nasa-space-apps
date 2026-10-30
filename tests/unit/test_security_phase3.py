import time
from datetime import timedelta
import pytest

from src.core.security import (
    InvalidTokenError,
    TokenExpiredError,
    _b64encode,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from src.modules.audit.service import sanitize_audit_metadata


def test_argon2_password_hashing_and_verification():
    """Verify password hashing with Argon2id produces valid salts and constant-time verification."""
    password = "SuperSecretAstroPassword123!"
    hashed = hash_password(password)

    # Must be valid Argon2id format
    assert hashed.startswith("$argon2id$")
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword!", hashed) is False

    # Distinct hashes for identical input (unique random salting)
    hashed_2 = hash_password(password)
    assert hashed != hashed_2


def test_password_hashing_empty_fails():
    """Verify empty password is rejected."""
    with pytest.raises(ValueError):
        hash_password("")


def test_valid_jwt_creation_and_decoding():
    """Verify valid JWT token encodes and decodes expected claims."""
    token = create_access_token(
        subject="astronaut_mark",
        role="CREW_MEMBER",
        crew_member_id="a1b2c3d4-0000-0000-0000-000000000001",
        assigned_crew_ids=None,
        expires_delta=timedelta(minutes=30),
    )
    claims = decode_access_token(token)

    assert claims["sub"] == "astronaut_mark"
    assert claims["role"] == "CREW_MEMBER"
    assert claims["crew_member_id"] == "a1b2c3d4-0000-0000-0000-000000000001"
    assert claims["iss"] == "nasa-space-apps-auth"
    assert claims["aud"] == "nasa-space-apps-api"
    assert claims["exp"] > time.time()


def test_expired_token_rejected():
    """Verify expired token raises TokenExpiredError."""
    # Negative delta produces an expired timestamp
    expired_token = create_access_token(
        subject="test_user",
        role="FLIGHT_SURGEON",
        expires_delta=timedelta(seconds=-10),
    )
    with pytest.raises(TokenExpiredError) as exc:
        decode_access_token(expired_token)
    assert "Token has expired" in str(exc.value)


def test_tampered_signature_rejected():
    """Verify modifying any payload character invalidates cryptographic signature."""
    token = create_access_token(subject="user_1", role="CREW_MEMBER")
    parts = token.split(".")

    # Tamper with signature
    tampered_sig = parts[2][:-2] + ("aa" if parts[2][-2:] != "aa" else "bb")
    tampered_token = f"{parts[0]}.{parts[1]}.{tampered_sig}"

    with pytest.raises(InvalidTokenError) as exc:
        decode_access_token(tampered_token)
    assert "Invalid token signature" in str(exc.value)


def test_malformed_token_format_rejected():
    """Verify invalid token formatting is rejected."""
    with pytest.raises(InvalidTokenError):
        decode_access_token("not-a-token")

    with pytest.raises(InvalidTokenError):
        decode_access_token("part1.part2")

    with pytest.raises(InvalidTokenError):
        decode_access_token("")


def test_algorithm_substitution_rejected():
    """Verify tokens signed with none algorithm or unapproved algorithms are rejected."""
    # Create fake token with {"alg": "none"}
    header = _b64encode(b'{"alg":"none","typ":"JWT"}')
    payload = _b64encode(b'{"sub":"hacker","role":"ADMIN","exp":9999999999,"iss":"nasa-space-apps-auth","aud":"nasa-space-apps-api"}')
    forged_token = f"{header}.{payload}."

    with pytest.raises(InvalidTokenError):
        decode_access_token(forged_token)


def test_audit_log_data_leakage_prevention():
    """Verify that credentials and sensitive medical payloads are stripped from audit metadata."""
    sensitive_metadata = {
        "client_ip": "192.168.1.50",
        "password": "ClearTextPassword123",
        "token": "secret-jwt-token-value",
        "value_numeric": 145.5,
        "controlled_notes": "Patient reported acute thoracic pain.",
        "findings": {"cardiac_alert": "HIGH"},
        "nested": {
            "secret_key": "some-secret",
            "safe_counter": 42,
        },
    }

    sanitized = sanitize_audit_metadata(sensitive_metadata)

    assert sanitized["client_ip"] == "192.168.1.50"
    assert sanitized["password"] == "[REDACTED]"
    assert sanitized["token"] == "[REDACTED]"
    assert sanitized["value_numeric"] == "[REDACTED]"
    assert sanitized["controlled_notes"] == "[REDACTED]"
    assert sanitized["findings"] == "[REDACTED]"
    assert sanitized["nested"]["secret_key"] == "[REDACTED]"
    assert sanitized["nested"]["safe_counter"] == 42

