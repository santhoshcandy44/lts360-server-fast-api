from datetime import datetime, timezone
from config import PROFILE_BASE_URL
import uuid

from fastapi import Request, UploadFile
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.users import User, UserLocation
from models.users import FCMToken

from helpers.response_helper import send_json_response, send_error_response
from utils.auth import generate_otp, send_otp_email
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


async def update_first_name(request: Request, body, db: AsyncSession):
    try:
        user = await _update_field(request.state.user.user_id, db, first_name=body.first_name)
        return send_json_response(200, "First name updated", data=_user_response(user))
    except Exception:
        return send_error_response(request, 500, "Internal server error")


async def update_last_name(request: Request, body, db: AsyncSession):
    try:
        user = await _update_field(request.state.user.user_id, db, last_name=body.last_name)
        return send_json_response(200, "Last name updated", data=_user_response(user))
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def update_about(request: Request, body, db: AsyncSession):
    try:
        user = await _update_field(request.state.user.user_id, db, about=body.about)
        return send_json_response(200, "About updated", data=_user_response(user))
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def update_account_type(request: Request, body, db: AsyncSession):
    try:
        user = await _get_user(request.state.user.user_id, db)
        if user.account_type == body.account_type:
            return send_error_response(request, 400, f"You are already in {body.account_type} account")

        user.account_type = body.account_type
        user.updated_at   = datetime.now(timezone.utc)
        db.add(user)
        await db.flush()
        await db.refresh(user)

        return send_json_response(200, "Account type updated", data=_user_response(user))
    except Exception:
        return send_error_response(request, 500, "Internal server error")


async def update_profile_pic(request: Request, profile_pic: UploadFile, db: AsyncSession):
    try:
        user_id  = request.state.user.user_id
        contents = await profile_pic.read()

        key        = f"profiles/{user_id}/{uuid.uuid4()}.jpg"
        key_96x96  = f"profiles/{user_id}/{uuid.uuid4()}_96x96.jpg"
        await upload_to_s3(contents, key, profile_pic.content_type)

        user = await _update_field(user_id, db, profile_pic_url=key, profile_pic_url_96x96=key_96x96)

        return send_json_response(200, "Profile picture updated", data=_user_response(user))
    except Exception:
        return send_error_response(request, 500, "Internal server error")


async def update_email(request: Request, body, db: AsyncSession):
    try:
        existing = await db.execute(select(User).where(User.email == body.email))
        if existing.scalar_one_or_none():
            return send_error_response(request, 409, "Email already in use")

        otp = generate_otp()
        save_otp(key=f"email_update_{body.email}", otp=otp, email=body.email)

        response = await send_otp_email(body.email, otp)
        if not response["success"]:
            return send_error_response(request, 500, "Failed to send OTP")

        return send_json_response(200, "OTP sent to new email")
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def update_email_otp_verify(request: Request, body, db: AsyncSession):
    try:
        key   = f"email_update_{body.email}"
        entry = get_otp(key)
        if not entry or is_expired(key):
            delete_otp(key)
            return send_error_response(request, 400, "OTP expired or not found")
        if entry["otp"] != body.otp:
            return send_error_response(request, 400, "Invalid OTP")

        user = await _update_field(
            request.state.user.user_id, db,
            email=body.email,
            is_email_verified=1,
        )
        if not user:
            return send_error_response(request, 404, "User not found")

        delete_otp(key)
        return send_json_response(200, "Email updated", data=_user_response(user))
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