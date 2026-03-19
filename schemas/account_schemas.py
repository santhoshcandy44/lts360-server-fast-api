from pydantic import BaseModel, EmailStr, field_validator
from typing import Literal
import re


class UpdateAccountTypeRequest(BaseModel):
    account_type: Literal["Personal", "Business"]


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password:     str

    @field_validator("current_password", "new_password")
    def validate_password(cls, v):
        if not 8 <= len(v) <= 16:
            raise ValueError("Password must be between 8 and 16 characters long")
        return v.strip()


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordVerifyOTPRequest(BaseModel):
    email: EmailStr
    otp:   str

    @field_validator("otp")
    def validate_otp(cls, v):
        if not re.match(r"^\d{6}$", v):
            raise ValueError("OTP must be exactly 6 digits and contain only numbers")
        return v


class ResetPasswordRequest(BaseModel):
    email:        EmailStr
    access_token: str
    password:     str

    @field_validator("password")
    def validate_password(cls, v):
        if not 8 <= len(v) <= 16:
            raise ValueError("Password must be between 8 and 16 characters long")
        return v.strip()