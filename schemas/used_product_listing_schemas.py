# schemas/used_product_schemas.py
from pydantic import BaseModel, field_validator, model_validator
from typing import Optional, List, Literal

VALID_STATES_IN = [
    "Andaman and Nicobar Islands", "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar",
    "Chandigarh", "Chhattisgarh", "Dadra and Nagar Haveli and Daman and Diu", "Delhi", "Goa",
    "Gujarat", "Haryana", "Himachal Pradesh", "Jammu and Kashmir", "Jharkhand", "Karnataka",
    "Kerala", "Ladakh", "Lakshadweep", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya",
    "Mizoram", "Nagaland", "Odisha", "Puducherry", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
    "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal"
]


class UsedProductLocationSchema(BaseModel):
    latitude:  float
    longitude: float

    @field_validator("latitude")
    def validate_latitude(cls, v):
        if not -90 <= v <= 90:
            raise ValueError("Latitude must be between -90 and 90")
        return v

    @field_validator("longitude")
    def validate_longitude(cls, v):
        if not -180 <= v <= 180:
            raise ValueError("Longitude must be between -180 and 180")
        return v


class CreateUsedProductListingRequest(BaseModel):
    name:            str
    description:     str
    country:         Literal["IN", "USA"]
    state:           str
    price:           float
    price_unit:      Literal["INR", "USD"]
    location:        UsedProductLocationSchema
    keep_image_ids:  Optional[List[int]] = None

    @field_validator("name")
    def validate_name(cls, v):
        if not 1 <= len(v) <= 100:
            raise ValueError("Name must be between 1 and 100 characters")
        return v.strip()

    @field_validator("description")
    def validate_description(cls, v):
        if not 1 <= len(v) <= 5000:
            raise ValueError("Description must be between 1 and 5000 characters")
        return v.strip()

    @field_validator("price")
    def validate_price(cls, v):
        if v < 0:
            raise ValueError("Price must be greater than or equal to 0")
        return v

    @field_validator("state")
    def validate_state(cls, v, info):
        country = info.data.get("country")
        if country == "IN" and v not in VALID_STATES_IN:
            raise ValueError("Invalid state for India")
        return v