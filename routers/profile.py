from database import get_db
from middleware.auth_middleware import authenticate_token

from fastapi import APIRouter, Depends, Request, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from schemas.profile_schemas import (
    UpdateFirstNameRequest,
    UpdateLastNameRequest,
    UpdateAboutRequest,
    UpdateEmailRequest,
    UpdateEmailVerifyOTPRequest,
    SendPhoneOTPRequest,
    VerifyPhoneOTPRequest,
    UpdateLocationRequest,
)

from controllers import profile_controller

router = APIRouter(
    prefix="/profile",
    tags=["Profile"],
    dependencies=[Depends(authenticate_token)],
)


@router.get("/")
async def get_profile(
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    return await profile_controller.get_profile(request, db)


@router.patch("/first-name")
async def update_first_name(
    body:    UpdateFirstNameRequest,
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    return await profile_controller.update_first_name(request, body, db)


@router.patch("/last-name")
async def update_last_name(
    body:    UpdateLastNameRequest,
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    return await profile_controller.update_last_name(request, body, db)


@router.patch("/about")
async def update_about(
    body:    UpdateAboutRequest,
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    return await profile_controller.update_about(request, body, db)


@router.patch("/profile-pic")
async def update_profile_pic(
    request:     Request,
    db:          AsyncSession = Depends(get_db),
    profile_pic: UploadFile   = File(...),
):
    return await profile_controller.update_profile_pic(request, profile_pic, db)


@router.patch("/email")
async def update_email(
    body:    UpdateEmailRequest,
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    return await profile_controller.update_email(request, body, db)


@router.patch("/email-verify-otp")
async def update_email_otp_verify(
    body:    UpdateEmailVerifyOTPRequest,
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    return await profile_controller.update_email_otp_verify(request, body, db)


@router.post("/phone/otp")
async def send_phone_otp(
    body:    SendPhoneOTPRequest,
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    return await profile_controller.send_phone_otp(request, body, db)


@router.post("/phone/verify-otp")
async def verify_phone_otp(
    body:    VerifyPhoneOTPRequest,
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    return await profile_controller.verify_phone_otp(request, body, db)


@router.put("/location")
async def update_location(
    body:    UpdateLocationRequest,
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    return await profile_controller.update_location(request, body, db)


@router.post("/logout")
async def log_out(
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    return await profile_controller.log_out(request, db)