from pydantic import BaseModel, EmailStr, field_validator
from typing import Literal
import re

class RegisterOTPSchema(BaseModel):
    email: EmailStr

    @field_validator("email")
    def validate_email(cls, v):
        if not v:
            raise ValueError("Email is required")
        return v

class VerifyOTPSchema(BaseModel):
    otp:          str
    first_name:   str
    last_name:    str
    email:        EmailStr
    password:     str
    account_type: Literal["Personal", "Business"]

    @field_validator("otp")
    def validate_otp(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("OTP is required")
        if not re.match(r"^\d{6}$", v):
            raise ValueError("OTP must be exactly 6 digits and contain only numbers")
        return v

    @field_validator("first_name")
    def validate_first_name(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("First name is required")
        if not 1 <= len(v) <= 70:
            raise ValueError("First name must be between 1 and 70 characters long")
        return v

    @field_validator("last_name")
    def validate_last_name(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Last name is required")
        if not 1 <= len(v) <= 50:
            raise ValueError("Last name must be between 1 and 50 characters long")
        return v

    @field_validator("email")
    def validate_email(cls, v):
        if not v:
            raise ValueError("Email is required")
        return v

    @field_validator("password")
    def validate_password(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Password is required")
        if not 8 <= len(v) <= 16:
            raise ValueError("Password must be between 8 and 16 characters long")
        return v

    @field_validator("account_type")
    def validate_account_type(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Account type is required")
        return v

class GoogleSignUpSchema(BaseModel):
    sign_up_method: Literal["google"]
    id_token:       str
    account_type:   Literal["Personal", "Business"]

    @field_validator("sign_up_method")
    def validate_sign_up_method(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Sign up method is required")
        return v

    @field_validator("id_token")
    def validate_id_token(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("ID Token is required")
        return v

    @field_validator("account_type")
    def validate_account_type(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Account type is required")
        return v

class EmailSignInSchema(BaseModel):
    email:    EmailStr
    password: str

    @field_validator("email")
    def validate_email(cls, v):
        if not v:
            raise ValueError("Email is required")
        return v

    @field_validator("password")
    def validate_password(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Password is required")
        if not 8 <= len(v) <= 16:
            raise ValueError("Password must be between 8 and 16 characters long")
        return v

class LTS360SignInSchema(BaseModel):
    email:    EmailStr
    password: str

    @field_validator("email")
    def validate_email(cls, v):
        if not v:
            raise ValueError("Email is required")
        return v

    @field_validator("password")
    def validate_password(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Password is required")
        if not 8 <= len(v) <= 16:
            raise ValueError("Password must be between 8 and 16 characters long")
        return v

class GoogleSignInSchema(BaseModel):
    sign_in_method: Literal["google"]
    id_token:       str

    @field_validator("sign_in_method")
    def validate_sign_in_method(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Sign in method is required")
        return v

    @field_validator("id_token")
    def validate_id_token(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("ID Token is required")
        return v

class GoogleLTS360SignInSchema(BaseModel):
    sign_in_method: Literal["google"]
    id_token:       str

    @field_validator("sign_in_method")
    def validate_sign_in_method(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Sign in method is required")
        return v

    @field_validator("id_token")
    def validate_id_token(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("ID Token is required")
        return v

class ForgotPasswordSchema(BaseModel):
    email: EmailStr

    @field_validator("email")
    def validate_email(cls, v):
        if not v:
            raise ValueError("Email is required")
        return v

class ForgotPasswordVerifyOTPSchema(BaseModel):
    otp:   str
    email: EmailStr

    @field_validator("otp")
    def validate_otp(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("OTP is required")
        if not re.match(r"^\d{6}$", v):
            raise ValueError("OTP must be exactly 6 digits and contain only numbers")
        return v

    @field_validator("email")
    def validate_email(cls, v):
        if not v:
            raise ValueError("Email is required")
        return v

class ResetPasswordSchema(BaseModel):
    email:    EmailStr
    password: str

    @field_validator("email")
    def validate_email(cls, v):
        if not v:
            raise ValueError("Email is required")
        return v

    @field_validator("password")
    def validate_password(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Password is required")
        if not 8 <= len(v) <= 16:
            raise ValueError("Password must be between 8 and 16 characters long")
        return v