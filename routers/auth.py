from fastapi import APIRouter, Request
from schemas.auth_schemas import (
    RegisterOTPRequest,
    VerifyOTPRequest,
    GoogleSignUpRequest,
    EmailSignInRequest,
    GoogleSignInRequest,
    ForgotPasswordRequest,
    ForgotPasswordVerifyOTPRequest,
    ResetPasswordRequest,
    RefreshTokenRequest,
)

router = APIRouter(
    prefix="/auth",
    tags=["Auth"],
)


@router.post("/register/otp")
async def register(body: RegisterOTPRequest, request: Request):
    pass


@router.post("/register/otp/verify")
async def verify_otp(body: VerifyOTPRequest, request: Request):
    pass


@router.post("/signup/google")
async def google_sign_up(body: GoogleSignUpRequest, request: Request):
    pass


@router.post("/signin/email")
async def email_sign_in(body: EmailSignInRequest, request: Request):
    pass


@router.post("/signin/lts360")
async def partner_email_sign_in(body: EmailSignInRequest, request: Request):
    pass


@router.post("/signin/google")
async def google_sign_in(body: GoogleSignInRequest, request: Request):
    pass


@router.post("/signin/google/lts360")
async def partner_google_sign_in(body: GoogleSignInRequest, request: Request):
    pass


@router.post("/forgot-password/otp")
async def forgot_password(body: ForgotPasswordRequest, request: Request):
    pass


@router.post("/forgot-password/otp/verify")
async def forgot_password_verify_otp(body: ForgotPasswordVerifyOTPRequest, request: Request):
    pass


@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest, request: Request):
    pass


@router.post("/refresh-token")
async def refresh_token(body: RefreshTokenRequest, request: Request):
    pass