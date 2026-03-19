
from datetime import datetime, timezone

from config import REFRESH_TOKEN_SECRET, PROFILE_BASE_URL
from helpers.response_helper import send_json_response, send_error_response

from jose import JWTError, jwt
from jose.jwt import get_unverified_claims  

from utils.auth import (
    generate_tokens, generate_salt, generate_pepper, hash_password,
    generate_forgot_password_token, decode_forgot_password_token,
    verify_id_token, generate_otp, send_otp_email,
)

from utils.otp_store import save_otp, get_otp, delete_otp, is_expired

from fastapi import Request
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.users import User
from .board_controller import create_default_boards_for_user, get_boards

def _build_user_response(result, profile_base_url: str) -> dict:
    return {
        "user_id":            result.user_id,
        "first_name":         result.first_name,
        "last_name":          result.last_name,
        "about":              result.about,
        "email":              result.email,
        "is_email_verified":  bool(result.is_email_verified),
        "phone_country_code": result.phone_country_code,
        "phone_number":       result.phone_number,
        "is_phone_verified":  bool(result.is_phone_verified),
        "profile_pic_url":    f"{profile_base_url}/{result.profile_pic_url}" if result.profile_pic_url else None,
        "account_type":       result.account_type,
        "created_at":         str(result.created_at.year) if result.created_at else None,
        "updated_at":         str(result.updated_at),
    }


async def _update_last_sign_in(user: User, db: AsyncSession) -> User:
    user.last_sign_in   = datetime.now(timezone.utc)
    user.account_status = "active"
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def register(request: Request, email: str, db: AsyncSession):
    try:
        result = await db.execute(select(User).where(User.email == email))
        if result.scalar_one_or_none():
            return send_error_response(request, 409, "Email in use with another account")

        otp = generate_otp()
        save_otp(key=email, otp=otp, email=email)

        response = await send_otp_email(email, otp)
        if not response["success"]:
            return send_error_response(request, 500, "Failed to send OTP")
        
        return send_json_response(200, "Email OTP has been sent")
    except Exception:
        return send_error_response(request, 500, "Internal Server Error")


async def verify_otp(request: Request, body, db: AsyncSession):
    try:
        entry = get_otp(body.email)
        if not entry:
            return send_error_response(request, 400, "OTP not found or expired")
        if is_expired(body.email):
            delete_otp(body.email)
            return send_error_response(request, 400, "OTP expired")
        if entry["otp"] != body.otp:
            return send_error_response(request, 400, "Invalid OTP")

        result = await db.execute(select(User).where(User.email == body.email))
        if result.scalar_one_or_none():
            return send_error_response(request, 409, "Email in use with another account")

        salt      = await generate_salt()
        pepper    = await generate_pepper()
        hashed_pw = await hash_password(pepper + body.password, salt)

        new_user = User(
            first_name=body.first_name,
            last_name=body.last_name,
            email=body.email,
            is_email_verified=1,
            account_type=body.account_type,
            sign_up_method="legacy_email",
            hashed_password=hashed_pw,
            pepper=pepper,
            salt=salt
        )
        db.add(new_user)
        await db.flush()

        new_user = await _update_last_sign_in(new_user, db)

        tokens = generate_tokens(new_user.user_id, new_user.email, "legacy_email", new_user.last_sign_in)
        await create_default_boards_for_user(new_user.user_id, db)
        boards = await get_boards(new_user.user_id, db)
        delete_otp(body.email)

        return send_json_response(201, "User registered successfully", data={
            "access_token":  tokens["accessToken"],
            "refresh_token": tokens["refreshToken"],
            "user":          _build_user_response(new_user, PROFILE_BASE_URL),
            "boards":        boards,
        })
    except Exception:
        return send_error_response(request, 500, "Internal server error")


async def google_sign_up(request: Request, body, db: AsyncSession):
    try:
        payload       = await verify_id_token(body.id_token)
        payload_email = payload.get("email")

        result = await db.execute(select(User).where(User.email == payload_email))
        if result.scalar_one_or_none():
            return send_error_response(request, 409, "Email is in use with another account")

        new_user = User(
            first_name=payload.get("given_name"),
            last_name=payload.get("family_name"),
            email=payload_email,
            is_email_verified=1,
            profile_pic_url=payload.get("picture"),
            account_type=body.account_type,
            sign_up_method="google",
        )
        db.add(new_user)
        await db.flush()

        new_user = await _update_last_sign_in(new_user, db)

        tokens = generate_tokens(new_user.user_id, new_user.email, "google", new_user.last_sign_in)
        await create_default_boards_for_user(new_user.user_id, db)
        boards = await get_boards(new_user.user_id, db)

        return send_json_response(201, "User registered successfully", data={
            "access_token":  tokens["accessToken"],
            "refresh_token": tokens["refreshToken"],
            "user":          _build_user_response(new_user, PROFILE_BASE_URL),
            "boards":        boards,
        })
    except Exception:
        return send_error_response(request, 500, "Internal server error")


async def email_sign_in(request: Request, body, db: AsyncSession):
    try:
        result = await db.execute(select(User).where(User.email == body.email))
        existing_user = result.scalar_one_or_none()
        if not existing_user:
            return send_error_response(request, 404, "Invalid user account")

        hashed_attempt = await hash_password(existing_user.pepper + body.password, existing_user.salt)
        if hashed_attempt != existing_user.hashed_password:
            return send_error_response(request, 400, "Invalid password")

        existing_user = await _update_last_sign_in(existing_user, db)
        tokens = generate_tokens(existing_user.user_id, existing_user.email, "legacy_email", existing_user.last_sign_in)
        boards = await get_boards(existing_user.user_id, db)

        return send_json_response(200, "User login successfully", data={
            "access_token":  tokens["accessToken"],
            "refresh_token": tokens["refreshToken"],
            "user":          _build_user_response(existing_user, PROFILE_BASE_URL),
            "boards":        boards,
        })
    except Exception:
        return send_error_response(request, 500, "Internal Server Error")


async def partner_email_sign_in(request: Request, body, db: AsyncSession):
    try:
        result = await db.execute(select(User).where(User.email == body.email))
        existing_user = result.scalar_one_or_none()
        if not existing_user:
            return send_error_response(request, 404, "Invalid user account")

        hashed_attempt = await hash_password(existing_user.pepper + body.password, existing_user.salt)
        if hashed_attempt != existing_user.hashed_password:
            return send_error_response(request, 400, "Invalid password")

        return send_json_response(200, "User login successfully", data={
            "user": _build_user_response(existing_user, PROFILE_BASE_URL),
        })
    except Exception:
        return send_error_response(request, 500, "Internal Server Error")


async def google_sign_in(request: Request, body, db: AsyncSession):
    try:
        payload       = await verify_id_token(body.id_token)
        payload_email = payload.get("email")
        if not payload_email:
            return send_error_response(request, 503, "Something went wrong")

        result = await db.execute(select(User).where(User.email == payload_email))
        existing_user = result.scalar_one_or_none()
        if not existing_user:
            return send_error_response(request, 404, "No account found")
        if existing_user.sign_up_method != "google":
            return send_error_response(request, 400, "This email is signed up with a different method")

        existing_user = await _update_last_sign_in(existing_user, db)
        tokens = generate_tokens(existing_user.user_id, existing_user.email, "google", existing_user.last_sign_in)
        boards = await get_boards(existing_user.user_id, db)

        return send_json_response(200, "User sign in successfully", data={
            "access_token":  tokens["accessToken"],
            "refresh_token": tokens["refreshToken"],
            "user":          _build_user_response(existing_user, PROFILE_BASE_URL),
            "boards":        boards,
        })
    except Exception:
        return send_error_response(request, 500, "Internal server error")


async def partner_google_sign_in(request: Request, body, db: AsyncSession):
    try:
        payload       = await verify_id_token(body.id_token)
        payload_email = payload.get("email")
        if not payload_email:
            return send_error_response(request, 503, "Something went wrong")

        result = await db.execute(select(User).where(User.email == payload_email))
        existing_user = result.scalar_one_or_none()
        if not existing_user:
            return send_error_response(request, 404, "No account found")
        if existing_user.sign_up_method != "google":
            return send_error_response(request, 400, "This email is signed up with a different method")

        return send_json_response(200, "User sign in successfully", data={
            "user_id":      existing_user.user_id,
            "user_details": _build_user_response(existing_user, PROFILE_BASE_URL),
        })
    except Exception:
        return send_error_response(request, 500, "Internal server error")


async def forgot_password(request: Request, body, db: AsyncSession):
    try:
        result = await db.execute(select(User).where(User.email == body.email))
        existing_user = result.scalar_one_or_none()
        if not existing_user:
            return send_error_response(request, 409, "Invalid user email")
        if existing_user.sign_up_method != "legacy_email":
            return send_error_response(request, 409, "Email is associated with different sign in method")

        otp = generate_otp()
        save_otp(key=f"forgot_{body.email}", otp=otp, email=body.email)

        response = await send_otp_email(body.email, otp)
        if not response["success"]:
            return send_error_response(request, 500, "Failed to send OTP")

        return send_json_response(200, "Email OTP has been sent")
    except Exception:
        return send_error_response(request, 400, "Internal Server Error")


async def forgot_password_verify_otp(request: Request, body, db: AsyncSession):
    try:
        key   = f"forgot_{body.email}"
        entry = get_otp(key)
        if not entry:
            return send_error_response(request, 403, "OTP not found or expired")
        if is_expired(key):
            delete_otp(key)
            return send_error_response(request, 403, "OTP has expired")
        if entry["otp"] != body.otp:
            return send_error_response(request, 400, "Invalid OTP")

        result = await db.execute(select(User).where(User.email == body.email))
        user = result.scalar_one_or_none()
        if not user:
            return send_error_response(request, 403, "User not exist")

        token = generate_forgot_password_token(user.user_id, user.email)
        delete_otp(key)

        return send_json_response(201, "OTP verified successfully", data={
            "email":        user.email,
            "access_token": token,
        })
    except Exception:
        return send_error_response(request, 400, "Internal Server Error")


async def reset_password(request: Request, body, db: AsyncSession):
    try:
        auth_header = request.headers.get("authorization")
        if not auth_header:
            return send_error_response(request, 401, "Access denied")
        token = auth_header.split(" ")[1] if " " in auth_header else None
        if not token:
            return send_error_response(request, 401, "Access denied")

        decoded = decode_forgot_password_token(token)
        user_id = decoded.get("userId")

        result = await db.execute(select(User).where(User.user_id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return send_error_response(request, 403, "User not exist")

        salt      = await generate_salt()
        pepper    = await generate_pepper()
        hashed_pw = await hash_password(pepper + body.password, salt)

        user.hashed_password = hashed_pw
        user.salt            = salt
        user.pepper          = pepper
        db.add(user)

        return send_json_response(200, "Password reset successfully")
    except Exception:
        return send_error_response(request, 400, "Internal Server Error")


async def refresh_token(request: Request, db: AsyncSession):
    try:
        auth_header = request.headers.get("authorization")
        if not auth_header:
            return send_error_response(request, 401, "Access denied")
        token = auth_header.split(" ")[1] if " " in auth_header else None
        if not token:
            return send_error_response(request, 401, "Access denied")

        try:
            payload = jwt.decode(token, REFRESH_TOKEN_SECRET, algorithms=["HS256"])
        except JWTError as e:
            if "expired" in str(e).lower():
                decoded = get_unverified_claims(token)
                user_id = decoded.get("userId")
                if user_id:
                    result = await db.execute(select(User).where(User.user_id == user_id))
                    user = result.scalar_one_or_none()
                    if user:
                        user.account_status = "deactivated"
                        db.add(user)
            return send_error_response(request, 403, "Unauthorized")

        result = await db.execute(select(User).where(User.user_id == payload["userId"]))
        existing_user = result.scalar_one_or_none()
        if not existing_user:
            return send_error_response(request, 403, "User not exist")

        tokens = generate_tokens(
            payload["userId"], payload["email"],
            payload["signUpMethod"], payload["lastSignIn"]
        )

        return send_json_response(201, "Authorized", data={
            "user_id":       existing_user.user_id,
            "access_token":  tokens["accessToken"],
            "refresh_token": tokens["refreshToken"],
        })
    except Exception:
        return send_error_response(request, 500, "Internal server error")