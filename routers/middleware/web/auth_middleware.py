from config.config import ACCESS_TOKEN_SECRET, ALGORITHM
from helpers.response_helper import AppException
from jose import jwt, JWTError
from jose.exceptions import JWTClaimsError

from db.database import get_db
from models.job import RecruiterProfile
from models.user import User

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select


async def authenticate_token(
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    try:
        token = request.cookies.get("access_token")

        if not token:
            raise AppException(401, "Missing token", "MISSING_TOKEN")

        try:
            payload = jwt.decode(token, ACCESS_TOKEN_SECRET, algorithms=[ALGORITHM])
        except (JWTError, JWTClaimsError) as e:
            raise AppException(401, "Invalid token", "INVALID_TOKEN")

        existing_user = await db.scalar(
            select(RecruiterProfile).where(RecruiterProfile.external_user_id == payload["userId"])
        )
        if not existing_user:
            raise AppException(401, "Something went wrong", "USER_NOT_FOUND")

        # if str(existing_user.last_sign_in) != payload.get("lastSignIn"):
        #     raise AppException(498, "Something went wrong", "INVALID_SESSION")

        request.state.user = existing_user
        return existing_user

    except AppException:
        raise
    except Exception as e:
        import traceback
        import sys
        traceback.print_exc(file=sys.stderr)
        sys.stderr.flush()
        print(e)
        raise AppException(500, "Internal server error", "SERVER_ERROR")