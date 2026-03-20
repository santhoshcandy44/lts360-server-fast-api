from datetime import datetime, timezone
import io
from config import PROFILE_BASE_URL
import uuid
from PIL import Image

from fastapi import Request, UploadFile
from schemas.account_schemas import ChangePasswordSchema, ForgotPasswordSchema, ForgotPasswordVerifyOTPSchema, ResetPasswordSchema, UpdateAccountTypeSchema
from schemas.profile_schemas import UpdateAboutSchema, UpdateEmailSchema, UpdateEmailVerifyOTPSchema, UpdateFirstNameSchema, UpdateLastNameSchema
from sqlmodel import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.users import User, UserLocation
from models.users import FCMToken

from helpers.response_helper import send_json_response, send_error_response
from utils.auth import compare_password, decode_forgot_password_token, generate_forgot_password_token, generate_otp, generate_pepper, generate_salt, generate_tokens, hash_password, send_otp_email
from utils.otp_store import save_otp, get_otp, delete_otp, is_expired
from utils.aws_s3 import upload_to_s3


async def update_account_type(request: Request, schema: UpdateAccountTypeSchema, db: AsyncSession):
    try:
        user_id = request.state.user.user_id
        user = await db.execute(select(User.account_type).where(User.user_id == user_id))
        user_result = user.first()
        if user_result.account_type == schema.account_type:
            return send_error_response(request, 400, f"You are already in {schema.account_type} account")
        await db.execute(
            update(User)
            .where(User.user_id == user_id)
            .values(account_type=schema.account_type)
        )
        db.flush()
        user = await db.execute(
            select(User.account_type, User.updated_at).where(User.user_id == user_id)
        )
        result = user.first()
        return send_json_response(200, f"Your account now on {result.account_type}", data={
            "account_type": result.account_type,
            "updated_at": str(result.updated_at),
        })
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def change_password(request: Request, schema: ChangePasswordSchema, db: AsyncSession):
    try:
        user_id = request.state.user.user_id
        user = await db.execute(select(User.pepper, User.salt, User.hashed_password).where(User.user_id == user_id))
        user_result = user.first()        
        if not await compare_password(user_result.pepper + schema.current_password, user_result.hashed_password):
            return send_error_response(request, 400, "Invalid password")

        salt = await generate_salt()
        pepper    = await generate_pepper()
        hashed_pw = await hash_password(pepper + schema.new_password, salt)

        await db.execute(
            update(User)
            .where(User.user_id == user_id)
            .values(salt = salt, pepper = pepper, hashed_password = hashed_pw)
        )
        return send_json_response(200, "Password changed successfully")
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def forgot_password(request: Request, schema: ForgotPasswordSchema, db: AsyncSession):
    try:
        email = schema.email

        result = await db.execute(select(User).where(User.email == email))
        existing_user = result.scalar_one_or_none()
        if not existing_user:
            return send_error_response(request, 409, "Invalid user email")
        if existing_user.sign_up_method != "legacy_email":
            return send_error_response(request, 409, "Email is associated with different sign in method")

        otp = generate_otp()
        await save_otp(key=f"forgot_{email}", otp=otp, email=email)

        response = await send_otp_email(email, otp)
        if not response["success"]:
            return send_error_response(request, 500, "Failed to send OTP")

        return send_json_response(200, "Email OTP has been sent")
    except Exception:
        return send_error_response(request, 400, "Internal Server Error")

async def forgot_password_verify_otp(request: Request, schema: ForgotPasswordVerifyOTPSchema, db: AsyncSession):
    try:
        email = schema.email
        otp = schema.otp

        key   = f"forgot_{email}"
        entry = await get_otp(key)
        if not entry:
            return send_error_response(request, 403, "OTP not found or expired")
        if await is_expired(key):
            await delete_otp(key)
            return send_error_response(request, 403, "OTP has expired")
        if entry["otp"] != otp:
            return send_error_response(request, 400, "Invalid OTP")

        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if not user:
            return send_error_response(request, 403, "User not exist")

        token = generate_forgot_password_token(user.user_id, user.email)
        await delete_otp(key)

        return send_json_response(201, "OTP verified successfully", data={
            "email":        user.email,
            "access_token": token,
        })
    except Exception:
        return send_error_response(request, 400, "Internal Server Error")

async def reset_password(request: Request, schmea: ResetPasswordSchema, db: AsyncSession):
    try:
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return send_error_response(request, 401, "Access denied")
        token = auth_header.split(" ")[1] if " " in auth_header else None
        if not token:
            return send_error_response(request, 401, "Access denied")

        decoded = decode_forgot_password_token(token)
        user_id = decoded.get("userId")

        user = await db.execute(select(User.pepper, User.salt, User.hashed_password).where(User.user_id == user_id))
        user_result = user.first()    
        if not user_result:
            return send_error_response(request, 403, "User not exist")

        salt      = await generate_salt()
        pepper    = await generate_pepper()
        hashed_pw = await hash_password(pepper + schmea.password, salt)

        await db.execute(
            update(User)
            .where(User.user_id == user_id)
            .values(salt = salt, pepper = pepper, hashed_password = hashed_pw)
        )
        return send_json_response(200, "Password reset successfully")
    except Exception:
        return send_error_response(request, 400, "Internal Server Error")

async def log_out(request: Request, db: AsyncSession):
    try:
        user_id = request.state.user.user_id
        await db.execute(
            update(User)
            .where(User.user_id == user_id)
            .values(account_status = "deactivated")
        )
        await db.execute(
        update(FCMToken)
        .where(FCMToken.user_id == user_id)
        .values(fcm_token=None)
        )
        return send_json_response(200, "Logged out successfully")
    except Exception:
        return send_error_response(request, 500, "Internal server error")