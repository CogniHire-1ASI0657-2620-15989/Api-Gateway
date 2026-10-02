import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> int:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticación requerido.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    settings = get_settings()
    try:
        claims = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key,
            algorithms=["HS256"],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
        )
        user_id = int(claims["sub"])
        if user_id <= 0:
            raise ValueError("Invalid subject")
    except (jwt.InvalidTokenError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticación inválido.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    return user_id
