from db.database import get_db
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from schemas.auth_schemas import (
    RegisterOTPSchema,
    VerifyOTPSchema,
    GoogleSignUpSchema,
    EmailSignInSchema,
    LTS360SignInSchema,
    GoogleSignInSchema,
    GoogleLTS360SignInSchema,
    ForgotPasswordSchema,
    ForgotPasswordVerifyOTPSchema,
    ResetPasswordSchema,
)

from services import auth_service

router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
)

@router.post("/register/otp")
async def register(
    schema:    RegisterOTPSchema,
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    return await auth_service.register(request, schema, db)

@router.post("/register/otp/verify")
async def verify_otp(
    schema:    VerifyOTPSchema,
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    return await auth_service.verify_otp(request, schema, db)

@router.post("/signup/google")
async def google_sign_up(
    schema:    GoogleSignUpSchema,
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    return await auth_service.google_sign_up(request, schema, db)


@router.post("/signin/email")
async def email_sign_in(
    request: Request,
    schema:    EmailSignInSchema,
    db:      AsyncSession = Depends(get_db),
):
    return await auth_service.email_sign_in(request, schema, db)

@router.post("/signin/google")
async def google_sign_in(
    request: Request,
    schema:    GoogleSignInSchema,
    db:      AsyncSession = Depends(get_db),
):
    return await auth_service.google_sign_in(request, schema, db)

@router.post("/signin/lts360")
async def partner_email_sign_in(
    request: Request,
    schema:    LTS360SignInSchema,
    db:      AsyncSession = Depends(get_db),
):
    return await auth_service.partner_email_sign_in(request, schema, db)

@router.post("/signin/lts360/google")
async def partner_google_sign_in(
    schema:    GoogleLTS360SignInSchema,
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    return await auth_service.partner_google_sign_in(request, schema, db)


@router.post("/forgot-password/otp")
async def forgot_password(
    schema:    ForgotPasswordSchema,
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    return await auth_service.forgot_password(request, schema, db)


@router.post("/forgot-password/otp/verify")
async def forgot_password_verify_otp(
    schema:    ForgotPasswordVerifyOTPSchema,
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    return await auth_service.forgot_password_verify_otp(request, schema, db)


@router.post("/reset-password")
async def reset_password(
    schema:    ResetPasswordSchema,
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    return await auth_service.reset_password(request, schema, db)


@router.post("/refresh-token")
async def refresh_token(
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    return await auth_service.refresh_token(request, db)