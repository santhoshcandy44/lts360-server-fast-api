from database import get_db
from helpers.response_helper import AppException
from .middleware.auth_middleware import authenticate_token

from fastapi import APIRouter, Depends, Request, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession

from schemas.profile_schemas import (
    UpdateProfilePicSchema,
    UpdateFirstNameSchema,
    UpdateLastNameSchema,
    UpdateAboutSchema,
    UpdateEmailSchema,
    UpdateEmailVerifyOTPSchema,
    SendPhoneOTPSchema,
    VerifyPhoneOTPSchema,
    UpdateLocationSchema,
)

from controllers import profile_controller

router = APIRouter(
    prefix="/profile",
    tags=["Profile"],
    dependencies=[Depends(authenticate_token)],
)


@router.get("")
async def get_profile(
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    return await profile_controller.get_profile(request, db)


@router.patch("/first-name")
async def update_first_name(
    body:    UpdateFirstNameSchema,
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    return await profile_controller.update_first_name(request, body, db)


@router.patch("/last-name")
async def update_last_name(
    body:    UpdateLastNameSchema,
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    return await profile_controller.update_last_name(request, body, db)


@router.patch("/about")
async def update_about(
    body:    UpdateAboutSchema,
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    return await profile_controller.update_about(request, body, db)


@router.patch("/profile-pic")
async def update_profile_pic(
    request:     Request,
    db:          AsyncSession = Depends(get_db),
    schema: UpdateProfilePicSchema   = Depends(),
):
    return await profile_controller.update_profile_pic(request, schema, db)


@router.patch("/email")
async def update_email(
    schema:    UpdateEmailSchema,
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    return await profile_controller.update_email(request, schema, db)

@router.patch("/email-verify-otp")
async def update_email_otp_verify(
    schema:    UpdateEmailVerifyOTPSchema,
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    return await profile_controller.update_email_otp_verify(request, schema, db)


@router.post("/phone/otp")
async def send_phone_otp(
    body:    SendPhoneOTPSchema,
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    return await profile_controller.send_phone_otp(request, body, db)


@router.post("/phone/verify-otp")
async def verify_phone_otp(
    body:    VerifyPhoneOTPSchema,
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    return await profile_controller.verify_phone_otp(request, body, db)


@router.put("/location")
async def update_location(
    body:    UpdateLocationSchema,
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    return await profile_controller.update_location(request, body, db)