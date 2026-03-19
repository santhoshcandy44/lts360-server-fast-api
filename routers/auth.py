from database import get_db
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from schemas.auth_schemas import (
    RegisterOTPRequest,
    VerifyOTPRequest,
    GoogleSignUpRequest,
    EmailSignInRequest,
    LTS360SignInRequest,
    GoogleSignInRequest,
    GoogleLTS360SignInRequest,
    ForgotPasswordRequest,
    ForgotPasswordVerifyOTPRequest,
    ResetPasswordRequest,
)

from controllers import auth_controller

router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
)


@router.post("/register/otp")
async def register(
    body:    RegisterOTPRequest,
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    return await auth_controller.register(request, body, db)


@router.post("/register/otp/verify")
async def verify_otp(
    body:    VerifyOTPRequest,
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    return await auth_controller.verify_otp(request, body, db)


@router.post("/signup/google")
async def google_sign_up(
    body:    GoogleSignUpRequest,
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    return await auth_controller.google_sign_up(request, body, db)


@router.post("/signin/email")
async def email_sign_in(
    body:    EmailSignInRequest,
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    return await auth_controller.email_sign_in(request, body, db)


@router.post("/signin/lts360")
async def partner_email_sign_in(
    body:    LTS360SignInRequest,
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    return await auth_controller.partner_email_sign_in(request, body, db)


@router.post("/signin/google")
async def google_sign_in(
    body:    GoogleSignInRequest,
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    return await auth_controller.google_sign_in(request, body, db)


@router.post("/signin/google/lts360")
async def partner_google_sign_in(
    body:    GoogleLTS360SignInRequest,
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    return await auth_controller.partner_google_sign_in(request, body, db)


@router.post("/forgot-password/otp")
async def forgot_password(
    body:    ForgotPasswordRequest,
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    return await auth_controller.forgot_password(request, body, db)


@router.post("/forgot-password/otp/verify")
async def forgot_password_verify_otp(
    body:    ForgotPasswordVerifyOTPRequest,
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    return await auth_controller.forgot_password_verify_otp(request, body, db)


@router.post("/reset-password")
async def reset_password(
    body:    ResetPasswordRequest,
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    return await auth_controller.reset_password(request, body, db)


@router.post("/refresh-token")
async def refresh_token(
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    return await auth_controller.refresh_token(request, db)