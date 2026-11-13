import uuid
from collections.abc import Callable
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.models.user import User

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
    session: AsyncSession = Depends(get_db),
) -> AuthenticatedIdentity:
    """Validates JWT and verifies the account is active in the database."""

    if credentials is None or not credentials.credentials:
        raise AppException(
            message="Missing or malformed Authorization header. Bearer token required.",
            code="unauthorized",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )

    token = credentials.credentials

    try:
        identity = default_identity_provider.validate_token(token)

        query = select(User).where(User.username == identity.username)
        result = await session.execute(query)
        user = result.scalar_one_or_none()

        if user is None or not user.is_active:
            raise AppException(
                message="Account is inactive or no longer exists.",
                code="unauthorized",
                status_code=status.HTTP_401_UNAUTHORIZED,
            )

        return AuthenticatedIdentity(
            user_id=str(user.id),
            username=user.username,
            role=user.role,
            crew_member_id=(
                str(user.crew_member_id) if user.crew_member_id else None
            ),
            assigned_crew_ids=[
                str(cid) for cid in (user.assigned_crew_ids or [])
            ],
        )

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

