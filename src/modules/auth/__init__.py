"""Authentication and authorization module."""
from src.modules.auth.identity_provider import (
    AuthenticatedIdentity,
    IdentityProvider,
    LocalDevIdentityProvider,
    default_identity_provider,
)
from src.modules.auth.schemas import (
    Token,
    TokenPayload,
    LoginRequest,
    UserCreate,
    UserRead,
)
from src.modules.auth.service import (
    AuthService,
    AuthenticationError,
    AuthorizationError,
)

__all__ = [
    "AuthenticatedIdentity",
    "IdentityProvider",
    "LocalDevIdentityProvider",
    "default_identity_provider",
    "Token",
    "TokenPayload",
    "LoginRequest",
    "UserCreate",
    "UserRead",
    "AuthService",
    "AuthenticationError",
    "AuthorizationError",
]
