# schemas/app_schemas.py
from pydantic import BaseModel, field_validator
from typing import Optional, List

class UpdateFCMTokenRequest(BaseModel):
    token: str

class UpdateE2EEPublicKeyRequest(BaseModel):
    public_key:  str
    key_version: int

    @field_validator("key_version")
    def validate_key_version(cls, v):
        if v < 0 or v == -1:
            raise ValueError("Key version cannot be negative or -1")
        return v

class Contact(BaseModel):
    country_code:  str
    local_number:  str
    full_number:   str


class SyncContactsRequest(BaseModel):
    contacts: List[Contact]

    @field_validator("contacts")
    def validate_contacts(cls, v):
        if len(v) < 1:
            raise ValueError("Contacts must be a non-empty array")
        return v