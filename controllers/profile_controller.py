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


def _user_response(user: User, location: UserLocation | None = None) -> dict:
    data = {
        "user_id":            user.user_id,
        "first_name":         user.first_name,
        "last_name":          user.last_name,
        "about":              user.about,
        "email":              user.email,
        "is_email_verified":  bool(user.is_email_verified),
        "phone_country_code": user.phone_country_code,
        "phone_number":       user.phone_number,
        "is_phone_verified":  bool(user.is_phone_verified),
        "profile_pic_url":    f"{PROFILE_BASE_URL}/{user.profile_pic_url}" if user.profile_pic_url else None,
        "profile_pic_url_96x96": f"{PROFILE_BASE_URL}/{user.profile_pic_url_96x96}" if user.profile_pic_url_96x96 else None,
        "account_type":       user.account_type,
        "created_at":         str(user.created_at.year) if user.created_at else None,
        "updated_at":         str(user.updated_at),
        "location": {
            "latitude":      location.latitude,
            "longitude":     location.longitude,
            "geo":           location.geo,
            "location_type": location.location_type,
            "updated_at":    str(location.updated_at),
        } if location else None,
    }
    return data

async def _get_user(user_id: int, db: AsyncSession) -> User | None:
    result = await db.execute(select(User).where(User.user_id == user_id))
    return result.scalar_one_or_none()


async def _update_field(user_id: int, db: AsyncSession, **fields) -> User | None:
    user = await _get_user(user_id, db)
    if not user:
        return None
    for key, value in fields.items():
        setattr(user, key, value)
    user.updated_at = datetime.now(timezone.utc)
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user

async def get_profile(request: Request, db: AsyncSession):
    try:
        user = request.state.user 
        await db.refresh(user)    
        return send_json_response(200, "Profile fetched", data=_user_response(user, user.location))
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def update_first_name(request: Request, schema: UpdateFirstNameSchema, db: AsyncSession):
    try:
        user_id = request.state.user.user_id
        await db.execute(
            update(User)
            .where(User.user_id == user_id)
            .values(first_name=schema.first_name)
        )
        await db.flush()
        user = await db.execute(
            select(User.first_name, User.updated_at).where(User.user_id == user_id)
        )
        result = user.first()
        return send_json_response(200, "First name updated", data={
            "first_name": result.first_name,
            "updated_at":  str(result.updated_at),
        })
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def update_last_name(request: Request, schema: UpdateLastNameSchema, db: AsyncSession):
    try:
        user_id = request.state.user.user_id
        await db.execute(
            update(User)
            .where(User.user_id == user_id)
            .values(last_name=schema.last_name)
        )
        db.flush()
        user = await db.execute(
            select(User.last_name, User.updated_at).where(User.user_id == user_id)
        )
        result = user.first()
        return send_json_response(200, "Last name updated", data={
            "last_name": result.last_name,
            "updated_at": str(result.updated_at),
        })
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def update_about(request: Request, schema: UpdateAboutSchema, db: AsyncSession):
    try:
        user_id = request.state.user.user_id
        await db.execute(
            update(User)
            .where(User.user_id == user_id)
            .values(about=schema.about)
        )
        db.flush()
        user = await db.execute(
            select(User.about, User.updated_at).where(User.user_id == user_id)
        )
        result = user.first()
        return send_json_response(200, "About updated", data={
            "about": result.about,
            "updated_at": str(result.updated_at),
        })
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def update_profile_pic(request: Request, profile_pic: UploadFile, db: AsyncSession):
    try:
        user_id  = request.state.user.user_id
        contents = await profile_pic.read()

        img = Image.open(io.BytesIO(contents))
        img = img.convert("RGB") 
        img_512x512 = img.resize((512, 512), Image.LANCZOS)

        buffer_512x512 = io.BytesIO()
        img_512x512.save(buffer_512x512, format="JPEG", quality=85)
        contents_512x512 = buffer_512x512.getvalue()

        img_small = Image.open(io.BytesIO(contents))
        img_small = img_small.convert("RGB") 
        img_96x96 = img_small.resize((96, 96), Image.LANCZOS)

        buffer_96x96 = io.BytesIO()
        img_96x96.save(buffer_96x96, format="JPEG", quality=85)
        contents_96x96 = buffer_96x96.getvalue()

        key       = f"profiles/{user_id}/{uuid.uuid4()}.jpg"
        key_96x96 = f"profiles/{user_id}/{uuid.uuid4()}_96x96.jpg"

        await upload_to_s3(contents_512x512,       key,       "image/jpeg")
        await upload_to_s3(contents_96x96, key_96x96, "image/jpeg")

        await db.execute(
            update(User)
            .where(User.user_id == user_id)
            .values(profile_pic_url=key,profile_pic_url_96x96=key_96x96)
        )
        db.flush()
        user = await db.execute(
            select(User.profile_pic_url, User.profile_pic_url_96x96, User.updated_at).where(User.user_id == user_id)
        )
        result = user.first()
        return send_json_response(200, "Profile picture updated", data={
            "profile_pic_url":    f"{PROFILE_BASE_URL}/{result.profile_pic_url}" if result.profile_pic_url else None,
            "updated_at": str(result.updated_at),
        })
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def update_email(request: Request, schema: UpdateEmailSchema, db: AsyncSession):
    try:
        existing = await db.execute(select(User).where(User.email == schema.email))
        if existing.scalar_one_or_none():
            return send_error_response(request, 409, "Email already in use")

        otp = generate_otp()
        await save_otp(key=f"email_update_{schema.email}", otp=otp, email=schema.email)

        response = await send_otp_email(schema.email, otp)
        if not response["success"]:
            return send_error_response(request, 500, "Failed to send OTP")

        return send_json_response(200, "OTP sent to new email")
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def update_email_otp_verify(request: Request, schema: UpdateEmailVerifyOTPSchema, db: AsyncSession):
    try:
        user_id = request.state.user.user_id
        key   = f"email_update_{schema.email}"
        entry = await get_otp(key)
        if not entry or await is_expired(key):
            await delete_otp(key)
            return send_error_response(request, 400, "OTP expired or not found")
        if entry["otp"] != schema.otp:
            return send_error_response(request, 400, "Invalid OTP")

        await db.execute(
                    update(User)
                    .where(User.user_id == user_id)
                    .values(about=schema.email)
                )
        await db.flush()
        user = await db.execute(
            select(User.email, User.sign_up_method, User.last_sign_in, User.updated_at).where(User.user_id == user_id)
        )
        result = user.first()
        tokens = generate_tokens(user_id, result.email, result.sign_up_method, result.last_sign_in)
        await delete_otp(key)
        return send_json_response(200, "Email updated", data={
            "email": result.email,
            "access_token": tokens["accessToken"],
            "refresh_token": tokens["refreshToken"],
            "updated_at": str(result.updated_at),
        })
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def send_phone_otp(request: Request, body, db: AsyncSession):
    try:
        otp = generate_otp()
        save_otp(key=f"phone_{body.phone_number}", otp=otp, email=body.phone_number)
        return send_json_response(200, "OTP sent to phone number")
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def verify_phone_otp(request: Request, body, db: AsyncSession):
    try:
        key   = f"phone_{body.phone_number}"
        entry = get_otp(key)
        if not entry or is_expired(key):
            delete_otp(key)
            return send_error_response(request, 400, "OTP expired or not found")
        if entry["otp"] != body.otp:
            return send_error_response(request, 400, "Invalid OTP")

        phone  = body.phone_number
        code   = phone[:3]   
        number = phone[3:]

        user = await _update_field(
            request.state.user.user_id, db,
            phone_country_code=code,
            phone_number=number,
            is_phone_verified=1,
        )
        delete_otp(key)
        return send_json_response(200, "Phone verified", data=_user_response(user))
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def update_location(request: Request, body, db: AsyncSession):
    try:
        user_id    = request.state.user.user_id
        loc_result = await db.execute(select(UserLocation).where(UserLocation.user_id == user_id))
        location   = loc_result.scalar_one_or_none()

        if location:
            location.latitude      = body.latitude
            location.longitude     = body.longitude
            location.geo           = body.geo
            location.location_type = body.location_type
            location.updated_at    = datetime.now(timezone.utc)
        else:
            location = UserLocation(
                user_id=user_id,
                latitude=body.latitude,
                longitude=body.longitude,
                geo=body.geo,
                location_type=body.location_type,
            )
        db.add(location)
        await db.flush()

        user = await _get_user(user_id, db)
        return send_json_response(200, "Location updated", data=_user_response(user, location))
    except Exception:
        return send_error_response(request, 500, "Internal server error")

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
        import traceback
        import sys
        traceback.print_exc(file=sys.stderr)
        sys.stderr.flush()
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
        import traceback
        import sys
        traceback.print_exc(file=sys.stderr)
        sys.stderr.flush()
        return send_error_response(request, 400, "Internal Server Error")


async def log_out(request: Request, db: AsyncSession):
    try:
        user_id = request.state.user.user_id
        await _update_field(user_id, db, account_status="deactivated")

        fcm_result = await db.execute(select(FCMToken).where(FCMToken.user_id == user_id))
        fcm = fcm_result.scalar_one_or_none()
        if fcm:
            fcm.fcm_token  = None
            fcm.updated_at = datetime.now(timezone.utc)
            db.add(fcm)

        return send_json_response(200, "Logged out successfully")
    except Exception:
        return send_error_response(request, 500, "Internal server error")