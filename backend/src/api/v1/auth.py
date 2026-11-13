
import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_identity, require_roles
from src.core.config import get_settings
from src.core.database import get_db
from src.modules.auth.identity_provider import (
    AuthenticatedIdentity,
    default_identity_provider,
)
from src.modules.auth.schemas import (
    LoginRequest,
    Token,
    UserCreate,
    UserRead,
)
from src.modules.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication & Accounts"])


@router.post(
    "/token",
    response_model=Token,
    status_code=status.HTTP_200_OK,
    summary="Obtain JWT Access Token",
    description="Authenticates with credentials using Argon2id verification and returns a signed RFC 7519 JWT.",
)
async def login_for_access_token(
    credentials: LoginRequest,
    session: AsyncSession = Depends(get_db),
) -> Token:
    token_str, _ = await default_identity_provider.authenticate(
        session=session,
        username=credentials.username,
        password=credentials.password,
    )
    settings = get_settings()
    return Token(
        access_token=token_str,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get(
    "/me",
    summary="Get Current Authenticated Identity",
    description="Returns the verified claims and role permissions of the currently authenticated identity.",
)
async def get_current_user_profile(
    identity: AuthenticatedIdentity = Depends(get_current_identity),
):
    return {
        "user_id": identity.user_id,
        "username": identity.username,
        "role": identity.role,
        "crew_member_id": identity.crew_member_id,
        "assigned_crew_ids": identity.assigned_crew_ids,
    }


@router.get(
    "/users",
    response_model=list[UserRead],
    summary="List Registered User Accounts",
    description="Returns registered account information. Restricted to ADMIN.",
)
async def list_user_accounts(
    session: AsyncSession = Depends(get_db),
    identity: AuthenticatedIdentity = Depends(require_roles("ADMIN")),
):
    return await AuthService.list_users(session=session)


@router.post(
    "/users",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create User Account",
    description="Creates a new account with hashed password. Restricted to ADMIN.",
)
async def create_user_account(
    user_in: UserCreate,
    session: AsyncSession = Depends(get_db),
    identity: AuthenticatedIdentity = Depends(require_roles("ADMIN")),
):
    new_user = await AuthService.create_user(
        session=session,
        user_in=user_in,
        requesting_actor=identity,
    )
    await session.commit()
    await session.refresh(new_user)
    return new_user


@router.get(
    "/crew/{target_crew_member_id}/access-verification",
    summary="Verify Object-Level Crew Access",
    description="Tests object-level authorization (BOLA prevention) for a given crew member identifier.",
)
async def verify_crew_access_endpoint(
    target_crew_member_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    identity: AuthenticatedIdentity = Depends(get_current_identity),
):
    await AuthService.enforce_crew_access(
        session=session,
        identity=identity,
        target_crew_member_id=target_crew_member_id,
        action="ACCESS_VERIFICATION",
    )
    return {
        "status": "authorized",
        "actor": identity.username,
        "role": identity.role,
        "target_crew_member_id": str(target_crew_member_id),
    }
