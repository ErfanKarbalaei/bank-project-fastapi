from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from asyncpg import Connection

from app.core.security import decode_access_token
from app.db.session import get_db_connection
from app.repositories.user_repo import UserRepository
from app.schemas.auth_schema import TokenPayload

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


async def get_current_user(
        token: str = Depends(oauth2_scheme),
        conn: Connection = Depends(get_db_connection),
) -> dict:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        if payload is None:
            raise credentials_exception
        token_data = TokenPayload(**payload)
    except JWTError:
        raise credentials_exception

    user_repo = UserRepository(conn)
    user_data = await user_repo.get_by_id(int(token_data.sub))

    if user_data is None:
        raise credentials_exception

    return user_data