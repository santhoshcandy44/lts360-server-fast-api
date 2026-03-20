from pydantic import BaseModel, EmailStr, field_validator
import re

class UpdateFirstNameSchema(BaseModel):
    first_name: str

    @field_validator("first_name")
    def validate_first_name(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("First name is required")
        if not 1 <= len(v) <= 70:
            raise ValueError("First name must be between 1 and 70 characters long")
        return v


class UpdateLastNameSchema(BaseModel):
    last_name: str

    @field_validator("last_name")
    def validate_last_name(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Last name is required")
        if not 1 <= len(v) <= 50:
            raise ValueError("Last name must be between 1 and 50 characters long")
        return v


class UpdateAboutSchema(BaseModel):
    about: str

    @field_validator("about")
    def validate_about(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("About is required")
        if not 1 <= len(v) <= 160:
            raise ValueError("About must be between 1 and 160 characters long")
        return v


class UpdateEmailSchema(BaseModel):
    email: EmailStr

    @field_validator("email")
    def validate_email(cls, v):
        if not v:
            raise ValueError("Email is required")
        return v


class UpdateEmailVerifyOTPSchema(BaseModel):
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

class SendPhoneOTPSchema(BaseModel):
    phone_number: str

    @field_validator("phone_number")
    def validate_phone_number(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Phone number is required")
        if not re.match(r"^\+?[1-9]\d{6,14}$", v):
            raise ValueError("Invalid phone number")
        return v

class VerifyPhoneOTPSchema(BaseModel):
    phone_number: str
    otp:          str

    @field_validator("phone_number")
    def validate_phone_number(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Phone number is required")
        if not re.match(r"^\+?[1-9]\d{6,14}$", v):
            raise ValueError("Invalid phone number")
        return v

    @field_validator("otp")
    def validate_otp(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("OTP is required")
        if not re.match(r"^\d{6}$", v):
            raise ValueError("OTP must be exactly 6 digits")
        return v

class UpdateLocationSchema(BaseModel):
    latitude:      float
    longitude:     float
    geo:           str
    location_type: str

    @field_validator("latitude")
    def validate_latitude(cls, v):
        if not -90 <= v <= 90:
            raise ValueError("Latitude must be a valid float")
        return v

    @field_validator("longitude")
    def validate_longitude(cls, v):
        if not -180 <= v <= 180:
            raise ValueError("Longitude must be a valid float")
        return v

    @field_validator("geo")
    def validate_geo(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Geo cannot be empty")
        return v

    @field_validator("location_type")
    def validate_location_type(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Location type cannot be empty")
        return v