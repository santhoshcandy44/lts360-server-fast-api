from fastapi import APIRouter, Depends, Request
from middleware.auth_middleware import authenticate_token
from schemas.account_schemas import (
    UpdateAccountTypeRequest,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ForgotPasswordVerifyOTPRequest,
    ResetPasswordRequest,
)

router = APIRouter(
    prefix="/account",
    tags=["Account"],
    dependencies=[Depends(authenticate_token)],
)


@router.patch("/account-type")
async def update_account_type(body: UpdateAccountTypeRequest, request: Request):
    pass


@router.put("/change-password")
async def change_password(body: ChangePasswordRequest, request: Request):
    pass


@router.post("/forgot-password/otp")
async def forgot_password(body: ForgotPasswordRequest, request: Request):
    pass


@router.post("/forgot-password/otp/verify")
async def forgot_password_otp_verify(body: ForgotPasswordVerifyOTPRequest, request: Request):
    pass


@router.post("/reset-password")
async def reset_password(body: ResetPasswordRequest, request: Request):
    pass