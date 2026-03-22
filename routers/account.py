from database import get_db
from .middleware.auth_middleware import authenticate_token

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from schemas.account_schemas import (
    UpdateAccountTypeSchema,
    ChangePasswordSchema,
    ForgotPasswordSchema,
    ForgotPasswordVerifyOTPSchema,
    ResetPasswordSchema,
)

from  controllers import account_controller

router = APIRouter(
    prefix="/account",
    tags=["Account"],
    dependencies=[Depends(authenticate_token)],
)

@router.patch("/account-type")
async def update_account_type(
    schema:    UpdateAccountTypeSchema,
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    return await account_controller.update_account_type(request, schema, db)


@router.put("/change-password")
async def change_password(
    schema:    ChangePasswordSchema,
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    return await account_controller.change_password(request, schema, db)


@router.post("/forgot-password/otp")
async def forgot_password(
    body:    ForgotPasswordSchema,
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    return await account_controller.forgot_password(request, body, db)


@router.post("/forgot-password/otp/verify")
async def forgot_password_otp_verify(
    body:    ForgotPasswordVerifyOTPSchema,
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    return await account_controller.forgot_password_verify_otp(request, body, db)


@router.post("/reset-password")
async def reset_password(
    body:    ResetPasswordSchema,
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    return await account_controller.reset_password(request, body, db)

@router.post("/logout")
async def log_out(
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    return await account_controller.log_out(request, db)