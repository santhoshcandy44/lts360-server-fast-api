from pydantic import BaseModel, EmailStr, field_validator
from typing import Literal
import re


class RegisterOTPRequest(BaseModel):
    email: EmailStr


class VerifyOTPRequest(BaseModel):
    otp:          str
    first_name:   str
    last_name:    str
    email:        EmailStr
    password:     str
    account_type: Literal["Personal", "Business"]

    @field_validator("otp")
    def validate_otp(cls, v):
        if not re.match(r"^\d{6}$", v):
            raise ValueError("OTP must be exactly 6 digits and contain only numbers")
        return v

    @field_validator("first_name")
    def validate_first_name(cls, v):
        if not 1 <= len(v) <= 70:
            raise ValueError("First name must be between 1 and 70 characters long")
        return v.strip()

    @field_validator("last_name")
    def validate_last_name(cls, v):
        if not 1 <= len(v) <= 50:
            raise ValueError("Last name must be between 1 and 50 characters long")
        return v.strip()

    @field_validator("password")
    def validate_password(cls, v):
        if not 8 <= len(v) <= 16:
            raise ValueError("Password must be between 8 and 16 characters long")
        return v.strip()


class GoogleSignUpRequest(BaseModel):
    sign_up_method: Literal["google"]
    id_token:       str
    account_type:   Literal["Personal", "Business"]


class EmailSignInRequest(BaseModel):
    email:    EmailStr
    password: str

    @field_validator("password")
    def validate_password(cls, v):
        if not 8 <= len(v) <= 16:
            raise ValueError("Password must be between 8 and 16 characters long")
        return v.strip()


class GoogleSignInRequest(BaseModel):
    sign_in_method: Literal["google"]
    id_token:       str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordVerifyOTPRequest(BaseModel):
    otp:   str
    email: EmailStr

    @field_validator("otp")
    def validate_otp(cls, v):
        if not re.match(r"^\d{6}$", v):
            raise ValueError("OTP must be exactly 6 digits and contain only numbers")
        return v


class ResetPasswordRequest(BaseModel):
    email:    EmailStr
    password: str

    @field_validator("password")
    def validate_password(cls, v):
        if not 8 <= len(v) <= 16:
            raise ValueError("Password must be between 8 and 16 characters long")
        return v.strip()


class RefreshTokenRequest(BaseModel):
    refresh_token: str