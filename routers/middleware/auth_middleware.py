from config import ACCESS_TOKEN_SECRET, ALGORITHM
from helpers.response_helper import AppException, send_error_response
from jose import jwt, JWTError
from jose.exceptions import JWTClaimsError

from database import get_db
from models.users import User

from fastapi import Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

bearer_scheme = HTTPBearer()

async def authenticate_token(
    request:     Request,
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    db:          AsyncSession = Depends(get_db),
):
    try:
        token = credentials.credentials

        try:
            payload = jwt.decode(token, ACCESS_TOKEN_SECRET, algorithms=[ALGORITHM])
        except (JWTError, JWTClaimsError):
            raise AppException(401, "Invalid token", "INVALID_TOKEN")

        existing_user = await db.scalar(
            select(User).where(User.user_id == payload["userId"])
        )
        if not existing_user:
            raise AppException(401, "User not found", "USER_NOT_FOUND")

        if str(existing_user.last_sign_in) != payload.get("lastSignIn"):
            raise AppException(498, "Invalid session", "INVALID_SESSION")

        request.state.user = existing_user
        return existing_user

    except AppException:
        raise 
    except Exception:
        raise AppException(500, "Internal server error", "SERVER_ERROR")