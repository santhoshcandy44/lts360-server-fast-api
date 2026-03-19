from database import get_db
from middleware.auth_middleware import authenticate_token

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from schemas.account_schemas import (
    UpdateAccountTypeRequest,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ForgotPasswordVerifyOTPRequest,
    ResetPasswordRequest,
)

from controllers import account_controller

router = APIRouter(
    prefix="/account",
    tags=["Account"],
    dependencies=[Depends(authenticate_token)],
)


@router.patch("/account-type")
async def update_account_type(
    body:    UpdateAccountTypeRequest,
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    return await account_controller.update_account_type(request, body, db)


@router.put("/change-password")
async def change_password(
    body:    ChangePasswordRequest,
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    return await account_controller.change_password(request, body, db)


@router.post("/forgot-password/otp")
async def forgot_password(
    body:    ForgotPasswordRequest,
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    return await account_controller.forgot_password(request, body, db)


@router.post("/forgot-password/otp/verify")
async def forgot_password_otp_verify(
    body:    ForgotPasswordVerifyOTPRequest,
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    return await account_controller.forgot_password_otp_verify(request, body, db)


@router.post("/reset-password")
async def reset_password(
    body:    ResetPasswordRequest,
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    return await account_controller.reset_password(request, body, db)