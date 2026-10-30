import uuid
from typing import Any
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import AppException
from src.core.security import hash_password
from src.models.user import User
from src.modules.audit.service import record_audit_event
from src.modules.auth.identity_provider import AuthenticatedIdentity
from src.modules.auth.schemas import UserCreate


class AuthorizationError(AppException):
    """Raised when an authenticated user lacks permission for an action or resource (HTTP 403)."""

    def __init__(self, message: str = "Access denied: insufficient permissions for this resource."):
        super().__init__(
            message=message,
            code="forbidden",
            status_code=403,
        )


class AuthenticationError(AppException):
    """Raised when authentication credentials or tokens are invalid (HTTP 401)."""

    def __init__(self, message: str = "Authentication required or invalid credentials."):
        super().__init__(
            message=message,
            code="unauthorized",
            status_code=401,
        )


class AuthService:
    """Authentication and Authorization domain service."""

    @staticmethod
    async def create_user(
        session: AsyncSession,
        user_in: UserCreate,
        requesting_actor: AuthenticatedIdentity | None = None,
    ) -> User:
        """Creates a new user account with secure password hashing and authorization checks."""
        # Check if any users exist in the system
        count_result = await session.execute(select(func.count(User.id)))
        user_count = count_result.scalar() or 0

        # If users exist, only an ADMIN can create new users
        if user_count > 0:
            if requesting_actor is None or requesting_actor.role != "ADMIN":
                raise AuthorizationError("Only administrators are permitted to create user accounts.")

        # Check for duplicate username
        existing = await session.execute(select(User).where(User.username == user_in.username))
        if existing.scalar_one_or_none() is not None:
            raise AppException(
                message=f"Username '{user_in.username}' is already taken.",
                code="USERNAME_TAKEN",
                status_code=400,
            )

        # Enforce role constraints
        if user_in.role == "CREW_MEMBER" and not user_in.crew_member_id:
            raise AppException(
                message="CREW_MEMBER role requires an associated crew_member_id.",
                code="MISSING_CREW_IDENTITY",
                status_code=400,
            )

        hashed = hash_password(user_in.password)
        assigned_ids_str = [str(uid) for uid in user_in.assigned_crew_ids]

        new_user = User(
            id=uuid.uuid4(),
            username=user_in.username,
            hashed_password=hashed,
            role=user_in.role,
            is_active=True,
            crew_member_id=user_in.crew_member_id,
            assigned_crew_ids=assigned_ids_str,
        )
        session.add(new_user)
        await session.flush()

        actor_name = requesting_actor.username if requesting_actor else "SYSTEM_BOOTSTRAP"
        await record_audit_event(
            session=session,
            actor=actor_name,
            action="CREATE_USER",
            resource_type="user",
            resource_id=str(new_user.id),
            metadata={"username": new_user.username, "role": new_user.role},
        )

        return new_user

    @staticmethod
    def verify_object_level_crew_access(
        identity: AuthenticatedIdentity,
        target_crew_member_id: str | uuid.UUID,
    ) -> bool:
        """Enforces strict Object-Level Authorization (BOLA prevention) across all roles.
        
        Rules:
          - CREW_MEMBER: Can only access records matching their personal crew_member_id.
          - FLIGHT_SURGEON: Can only access records of crew explicitly in their assigned_crew_ids.
          - ADMIN: Does NOT have automatic access to clinical records unless explicitly assigned!
        """
        target_str = str(target_crew_member_id).lower()

        if identity.role == "CREW_MEMBER":
            if not identity.crew_member_id:
                return False
            return str(identity.crew_member_id).lower() == target_str

        if identity.role == "FLIGHT_SURGEON":
            assigned_lower = [str(cid).lower() for cid in identity.assigned_crew_ids]
            return target_str in assigned_lower

        if identity.role == "ADMIN":
            # Least-privilege principle: Admins have zero automatic access to clinical health records!
            assigned_lower = [str(cid).lower() for cid in identity.assigned_crew_ids]
            return target_str in assigned_lower

        return False

    @classmethod
    async def enforce_crew_access(
        cls,
        session: AsyncSession,
        identity: AuthenticatedIdentity,
        target_crew_member_id: str | uuid.UUID,
        action: str = "ACCESS_HEALTH_RECORD",
    ) -> None:
        """Enforces object-level access and logs authorization failures for security auditing."""
        has_access = cls.verify_object_level_crew_access(identity, target_crew_member_id)

        if not has_access:
            # Audit the authorization failure
            await record_audit_event(
                session=session,
                actor=identity.username,
                action="AUTHORIZATION_FAILURE",
                resource_type="crew_health_record",
                resource_id=str(target_crew_member_id),
                metadata={
                    "actor_role": identity.role,
                    "attempted_action": action,
                    "reason": "Object-level authorization denied",
                },
            )
            raise AuthorizationError(
                f"User '{identity.username}' is not authorized to access health records for crew '{target_crew_member_id}'."
            )

