from datetime import datetime, timezone
import io
from config import PROFILE_BASE_URL
import uuid
from PIL import Image

from fastapi import Request, UploadFile
from schemas.account_schemas import ChangePasswordSchema, ForgotPasswordSchema, ForgotPasswordVerifyOTPSchema, ResetPasswordSchema, UpdateAccountTypeSchema
from schemas.profile_schemas import SendPhoneOTPSchema, UpdateAboutSchema, UpdateEmailSchema, UpdateEmailVerifyOTPSchema, UpdateFirstNameSchema, UpdateLastNameSchema, UpdateLocationSchema, VerifyPhoneOTPSchema
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

async def send_phone_otp(request: Request, body:SendPhoneOTPSchema, db: AsyncSession):
    try:
        otp = generate_otp()
        await save_otp(key=f"phone_{body.phone_number}", otp=otp, email=body.phone_number)
        return send_json_response(200, "OTP sent to phone number")
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def verify_phone_otp(request: Request, body:VerifyPhoneOTPSchema, db: AsyncSession):
    try:
        key   = f"phone_{body.phone_number}"
        entry = await get_otp(key)
        if not entry or await is_expired(key):
            await delete_otp(key)
            return send_error_response(request, 400, "OTP expired or not found")
        if entry["otp"] != body.otp:
            return send_error_response(request, 400, "Invalid OTP")

        phone  = body.phone_number
        code   = phone[:3]   
        number = phone[3:]

        user_id = request.state.user.user_id

        await db.execute(
               update(User)
                    .where(User.user_id == user_id)
                    .values(phone_country_code=code, phone_number=number, is_phone_verified=1)     
         )
        db.flush()
        user = await db.execute(
            select(User.phone_country_code, User.phone_number, User.is_phone_verified, User.updated_at).where(User.user_id == user_id)
        )
        result = user.first()
        await delete_otp(key)
        return send_json_response(200, "Phone verified", data={
            "country_code": result.phone_country_code,
            "number": result.phone_number,
            "is_phone_verified": result.is_phone_verified,
            "updated_at": str(result.updated_at),
        })
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def update_location(request: Request, schema:UpdateLocationSchema, db: AsyncSession):
    try:
        user_id    = request.state.user.user_id
        loc_result = await db.execute(select(UserLocation).where(UserLocation.user_id == user_id))
        location   = loc_result.scalar_one_or_none()

        if location:
            location.latitude      = schema.latitude
            location.longitude     = schema.longitude
            location.geo           = schema.geo
            location.location_type = schema.location_type
        else:
            location = UserLocation(
                user_id=user_id,
                latitude=schema.latitude,
                longitude=schema.longitude,
                geo=schema.geo,
                location_type=schema.location_type,
            )
        db.add(location)
        await db.flush()

        return send_json_response(200, "Location updated", data={
            "location_type": location.location_type,
            "latitude": location.latitude,
            "longitude": location.longitude,
            "geo": location.geo,
            "updated_at": str(location.updated_at),
        })
    except Exception:
        return send_error_response(request, 500, "Internal server error")