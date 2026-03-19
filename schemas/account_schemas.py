from pydantic import BaseModel, EmailStr, field_validator
from typing import Literal
import re


class UpdateAccountTypeRequest(BaseModel):
    account_type: Literal["Personal", "Business"]

    @field_validator("account_type")
    def validate_account_type(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Account type is required")
        return v


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password:     str

    @field_validator("current_password")
    def validate_current_password(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Current password is required")
        if not 8 <= len(v) <= 16:
            raise ValueError("Current password must be between 8 and 16 characters long")
        return v

    @field_validator("new_password")
    def validate_new_password(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("New password is required")
        if not 8 <= len(v) <= 16:
            raise ValueError("New password must be between 8 and 16 characters long")
        return v


class ForgotPasswordRequest(BaseModel):
    email: EmailStr

    @field_validator("email")
    def validate_email(cls, v):
        if not v:
            raise ValueError("Email is required")
        return v


class ForgotPasswordVerifyOTPRequest(BaseModel):
    email: EmailStr
    otp:   str

    @field_validator("email")
    def validate_email(cls, v):
        if not v:
            raise ValueError("Email is required")
        return v

    @field_validator("otp")
    def validate_otp(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("OTP is required")
        if not re.match(r"^\d{6}$", v):
            raise ValueError("OTP must be exactly 6 digits and contain only numbers")
        return v


class ResetPasswordRequest(BaseModel):
    email:        EmailStr
    access_token: str
    password:     str

    @field_validator("email")
    def validate_email(cls, v):
        if not v:
            raise ValueError("Email is required")
        return v

    @field_validator("access_token")
    def validate_access_token(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Token must be a valid string")
        return v

    @field_validator("password")
    def validate_password(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Password is required")
        if not 8 <= len(v) <= 16:
            raise ValueError("Password must be between 8 and 16 characters long")
        return v