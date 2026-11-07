import uuid
from collections.abc import Callable
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.core.exceptions import AppException
from src.core.security import InvalidTokenError, TokenExpiredError
from src.modules.auth.identity_provider import (
    AuthenticatedIdentity,
    default_identity_provider,
)
from src.modules.auth.service import AuthService, AuthorizationError

security_scheme = HTTPBearer(auto_error=False)


async def get_current_identity(
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
) -> AuthenticatedIdentity:
    """Extracts and cryptographically validates the Bearer token."""
    if credentials is None or not credentials.credentials:
        raise AppException(
            message="Missing or malformed Authorization header. Bearer token required.",
            code="unauthorized",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    token = credentials.credentials
    try:
        identity = default_identity_provider.validate_token(token)
        return identity
    except TokenExpiredError as exc:
        raise AppException(
            message=str(exc),
            code="unauthorized",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    except InvalidTokenError as exc:
        raise AppException(
            message=str(exc),
            code="unauthorized",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )


def require_roles(*allowed_roles: str) -> Callable:
    """Role-Based Access Control (RBAC) dependency factory."""

    async def role_checker(
        identity: AuthenticatedIdentity = Depends(get_current_identity),
    ) -> AuthenticatedIdentity:
        if identity.role not in allowed_roles:
            raise AppException(
                message=(
                    f"Role '{identity.role}' does not have required permissions. "
                    f"Required one of: {list(allowed_roles)}"
                ),
                code="forbidden",
                status_code=status.HTTP_403_FORBIDDEN,
            )
        return identity

    return role_checker


async def verify_crew_access_dependency(
    target_crew_member_id: uuid.UUID,
    identity: AuthenticatedIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_db),
) -> AuthenticatedIdentity:
    """Object-level authorization dependency preventing cross-crew data tampering and inspection."""
    await AuthService.enforce_crew_access(
        session=session,
        identity=identity,
        target_crew_member_id=target_crew_member_id,
        action="ACCESS_HEALTH_RECORD",
    )
    return identity

