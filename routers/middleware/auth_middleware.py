

from config import ACCESS_TOKEN_SECRET, ALGORITHM
from helpers.response_helper import send_error_response
from jose import JWTError, jwt

from database import get_db
from models.users import User

from fastapi import Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

bearer_scheme = HTTPBearer()

async def authenticate_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
):
    try:
        token = credentials.credentials

        try:
            payload = jwt.decode(token, ACCESS_TOKEN_SECRET, algorithms=[ALGORITHM])
        except JWTError:
            return send_error_response(request, 401, "Invalid token access denied", error_code="INVALID_TOKEN")

        user_id      = payload.get("userId")
        last_sign_in = payload.get("lastSignIn")

        if not user_id:
            return send_error_response(request, 401, "No valid token access denied", error_code="NO_TOKEN")

        result = await db.execute(select(User).where(User.user_id == int(user_id)))
        existing_user = result.scalar_one_or_none()

        if not existing_user:
            return send_error_response(request, 401, "User not exist access denied", error_code="USER_NOT_FOUND")

        if last_sign_in != str(existing_user.last_sign_in):
            return send_error_response(request, 498, "Invalid session", error_code="INVALID_SESSION")

        request.state.user = existing_user

        return existing_user
    except Exception :
                    return send_error_response(request, 500, "Internal server error", "SERVER_ERROR")