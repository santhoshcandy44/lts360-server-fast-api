# routers/profile.py
from fastapi import APIRouter, Depends, Request, UploadFile, File
from middleware.auth_middleware import authenticate_token
from schemas.profile_schemas import (
    UpdateFirstNameRequest,
    UpdateLastNameRequest,
    UpdateAboutRequest,
    UpdateEmailRequest,
    UpdateEmailOtpVerifyRequest,
    SendPhoneOtpRequest,
    VerifyPhoneOtpRequest,
    UpdateLocationRequest,
)

router = APIRouter(
    prefix="/profile",
    tags=["Profile"],
    dependencies=[Depends(authenticate_token)],
)


@router.get("/")
async def get_profile(request: Request):
    pass


@router.patch("/first-name")
async def update_first_name(body: UpdateFirstNameRequest, request: Request):
    pass


@router.patch("/last-name")
async def update_last_name(body: UpdateLastNameRequest, request: Request):
    pass


@router.patch("/about")
async def update_about(body: UpdateAboutRequest, request: Request):
    pass


@router.patch("/profile-pic")
async def update_profile_pic(
    request:     Request,
    profile_pic: UploadFile = File(...),     # max 5MB, jpeg/png/webp/gif
):
    pass


@router.patch("/email")
async def update_email(body: UpdateEmailRequest, request: Request):
    pass


@router.patch("/email-verify-otp")
async def update_email_otp_verify(body: UpdateEmailOtpVerifyRequest, request: Request):
    pass


@router.post("/phone/otp")
async def send_phone_otp(body: SendPhoneOtpRequest, request: Request):
    pass


@router.post("/phone/verify-otp")
async def verify_phone_otp(body: VerifyPhoneOtpRequest, request: Request):
    pass


@router.put("/location")
async def update_location(body: UpdateLocationRequest, request: Request):
    pass


@router.post("/logout")
async def log_out(request: Request):
    pass