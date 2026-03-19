from pydantic import BaseModel, EmailStr, field_validator
from typing import Literal
import re

class UpdateFirstNameRequest(BaseModel):
    first_name: str

    @field_validator("first_name")
    def validate_first_name(cls, v):
        if not 1 <= len(v) <= 70:
            raise ValueError("First name must be between 1 and 70 characters long")
        return v.strip()


class UpdateLastNameRequest(BaseModel):
    last_name: str

    @field_validator("last_name")
    def validate_last_name(cls, v):
        if not 1 <= len(v) <= 50:
            raise ValueError("Last name must be between 1 and 50 characters long")
        return v.strip()


class UpdateAboutRequest(BaseModel):
    about: str

    @field_validator("about")
    def validate_about(cls, v):
        if not 1 <= len(v) <= 160:
            raise ValueError("About must be between 1 and 160 characters long")
        return v.strip()


class UpdateEmailRequest(BaseModel):
    email: EmailStr


class UpdateEmailOtpVerifyRequest(BaseModel):
    email: EmailStr
    otp:   str

    @field_validator("otp")
    def validate_otp(cls, v):
        if not re.match(r"^\d{6}$", v):
            raise ValueError("OTP must be exactly 6 digits and contain only numbers")
        return v.strip()


class SendPhoneOtpRequest(BaseModel):
    phone_number: str

    @field_validator("phone_number")
    def validate_phone(cls, v):
        if not v.strip():
            raise ValueError("Phone number is required")
        return v.strip()


class VerifyPhoneOtpRequest(BaseModel):
    phone_number: str
    otp:          str

    @field_validator("otp")
    def validate_otp(cls, v):
        if not re.match(r"^\d{6}$", v):
            raise ValueError("OTP must be exactly 6 digits")
        return v


class UpdateLocationRequest(BaseModel):
    latitude:      float
    longitude:     float
    geo:           str
    location_type: Literal["approximate", "precise"]