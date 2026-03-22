from pydantic import BaseModel, field_validator
from typing import Optional, List


class UpdateFCMTokenRequest(BaseModel):
    token: str

    @field_validator("token")
    def validate_token(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("FCM token is required")
        return v


class UpdateE2EEPublicKeyRequest(BaseModel):
    public_key:  str
    key_version: int

    @field_validator("public_key")
    def validate_public_key(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Public key is required")
        return v

    @field_validator("key_version")
    def validate_key_version(cls, v):
        if v < 0 or v == -1:
            raise ValueError("Key version cannot be negative or -1")
        return v


class Contact(BaseModel):
    country_code: str
    local_number: str
    full_number:  str

    @field_validator("country_code", "local_number", "full_number")
    def validate_not_empty(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Field cannot be empty")
        return v


class SyncContactsRequest(BaseModel):
    contacts: List[Contact]

    @field_validator("contacts")
    def validate_contacts(cls, v):
        if len(v) < 1:
            raise ValueError("Contacts must be a non-empty array")
        return v


class GetBookmarksSchema(BaseModel):
    page_size:      Optional[int] = 20
    next_token:     Optional[str] = None
    previous_token: Optional[str] = None

    @field_validator("page_size")
    def validate_page_size(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Page size must be a positive integer")
        if v is not None and v > 100:
            raise ValueError("Page size must not exceed 100")
        return v

    @field_validator("next_token", "previous_token")
    def validate_token(cls, v):
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Token must not be an empty string")
        return v


class SearchChatsRequest(BaseModel):
    search: str

    @field_validator("search")
    def validate_search(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Search cannot be empty")
        return v


class LookupByPhoneRequest(BaseModel):
    country_code: str
    local_number: str

    @field_validator("country_code", "local_number")
    def validate_not_empty(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Field cannot be empty")
        return v