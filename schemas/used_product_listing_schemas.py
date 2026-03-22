from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ValidationError, field_validator, model_validator
from typing import Annotated, Optional, List, Literal
from fastapi import Form, UploadFile , File
import json

VALID_COUNTRIES     = ['IN', 'USA']
VALID_INDIAN_STATES = [
    "Andaman and Nicobar Islands", "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar",
    "Chandigarh", "Chhattisgarh", "Dadra and Nagar Haveli and Daman and Diu", "Delhi", "Goa",
    "Gujarat", "Haryana", "Himachal Pradesh", "Jammu and Kashmir", "Jharkhand", "Karnataka",
    "Kerala", "Ladakh", "Lakshadweep", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya",
    "Mizoram", "Nagaland", "Odisha", "Puducherry", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
    "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal"
]

MAX_IMAGE_SIZE    = 1 * 1024 * 1024  
ALLOWED_TYPES     = ["image/jpeg", "image/png", "image/webp"]

class GuestGetUsedProductListingsSchema(BaseModel):
    s:              Optional[str]   = None
    latitude:       Optional[float] = None
    longitude:      Optional[float] = None
    page_size:      Optional[int]   = None
    next_token:     Optional[str]   = None
    previous_token: Optional[str]   = None

    @field_validator("s")
    def validate_s(cls, v):
        if v is not None:
            v = v.strip()
            if len(v) > 100:
                raise ValueError("Search must be between 0 and 100 characters")
        return v

    @field_validator("latitude")
    def validate_latitude(cls, v):
        if v is not None and not -90 <= v <= 90:
            raise ValueError("Latitude must be between -90 and 90")
        return v

    @field_validator("longitude")
    def validate_longitude(cls, v):
        if v is not None and not -180 <= v <= 180:
            raise ValueError("Longitude must be between -180 and 180")
        return v

    @field_validator("page_size")
    def validate_page_size(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Page size must be a positive integer")
        return v

class GetUsedProductListingsSchema(BaseModel):
    s:              Optional[str] = None
    page_size:      Optional[int] = None
    next_token:     Optional[str] = None
    previous_token: Optional[str] = None

    @field_validator("s")
    def validate_s(cls, v):
        if v is not None:
            v = v.strip()
            if len(v) > 100:
                raise ValueError("Search must be between 0 and 100 characters")
        return v

    @field_validator("page_size")
    def validate_page_size(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Page size must be a positive integer")
        return v

class UsedProductListingIdParam(BaseModel):
    used_product_listing_id: int

    @field_validator("used_product_listing_id")
    def validate_id(cls, v):
        if v <= 0:
            raise ValueError("Invalid used product listing id")
        return v
    
class GetUserProfileUsedProductListingsSchema(BaseModel):
    user_id: int
    page_size: Optional[int] = None

    @field_validator("user_id")
    def validate_user_id(cls, v):
        if v <= 0:
            raise ValueError("Invalid user id")
        return v

    @field_validator("page_size")
    def validate_page_size(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Page size must be a positive integer")
        return v

class GetUsedProductListingsByUserIdSchema(BaseModel):
    page_size:      Optional[int] = None
    next_token:     Optional[str] = None
    previous_token: Optional[str] = None

    @field_validator("page_size")
    def validate_page_size(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Page size must be a positive integer")
        return v

class GetPublishedUsedProductListingsSchema(BaseModel):
    page_size:      Optional[int] = None
    next_token:     Optional[str] = None
    previous_token: Optional[str] = None

    @field_validator("page_size")
    def validate_page_size(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Page size must be a positive integer")
        return v

class CreateOrUpdateUsedProductListingSchema(BaseModel):
    used_product_listing_id: int
    name:                    str
    description:             str
    country:                 str
    state:                   str
    keep_image_ids:          Optional[List[int]] = None
    price:                   float
    price_unit:              Literal["INR", "USD"]
    location:                str
    images:                  Optional[List[UploadFile]] = None

    @field_validator("name")
    def validate_name(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Name is required")
        if not 1 <= len(v) <= 100:
            raise ValueError("Name must be between 1 and 100 characters long")
        return v

    @field_validator("description")
    def validate_description(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Description is required")
        if not 1 <= len(v) <= 5000:
            raise ValueError("Description must be between 1 and 5000 characters long")
        return v

    @field_validator("country")
    def validate_country(cls, v):
        if v not in VALID_COUNTRIES:
            raise ValueError("Invalid country")
        return v

    @field_validator("price")
    def validate_price(cls, v):
        if v < 0:
            raise ValueError("Price must be >= 0")
        return v

    @field_validator("keep_image_ids", mode="before")
    def validate_keep_image_ids(cls, v):
        if v is None:
            return None
        if not isinstance(v, list):
            v = [v]
        return [int(i) for i in v]

    @field_validator("location")
    def validate_location(cls, v):
        try:
            parsed = json.loads(v)
        except Exception:
            raise ValueError("Location must be a valid JSON object")
        if not isinstance(parsed, dict):
            raise ValueError("Location must be a valid JSON object")
        lat = parsed.get("latitude")
        lng = parsed.get("longitude")
        if lat is None or lng is None:
            raise ValueError("Location must have latitude and longitude")
        if not -90 <= float(lat) <= 90:
            raise ValueError("Latitude must be between -90 and 90")
        if not -180 <= float(lng) <= 180:
            raise ValueError("Longitude must be between -180 and 180")
        return parsed  

    @model_validator(mode="after")
    def validate_state(self):
        if self.country == "IN" and self.state not in VALID_INDIAN_STATES:
            raise ValueError("Invalid state for India")
        return self
    
    @model_validator(mode="after")
    def validate_images_and_keep(self):
        has_new_images  = self.images and len(self.images) > 0
        has_kept_images = self.keep_image_ids and len(self.keep_image_ids) > 0
        if not has_new_images and not has_kept_images:
            raise ValueError("At least 1 image is required")

        if self.images:
            for image in self.images:
                if image.content_type not in ALLOWED_TYPES:
                    raise ValueError(f"Invalid file type: {image.filename}")
                if image.size and image.size > MAX_IMAGE_SIZE:
                    raise ValueError(f"Image {image.filename} must be under 1MB")
        return self

async def create_or_update_used_product_listing_form(
    used_product_listing_id: int                  = Form(...),
    name:                    str                  = Form(...),
    description:             str                  = Form(...),
    country:                 str                  = Form(...),
    state:                   str                  = Form(...),
    price:                   float                = Form(...),
    price_unit:              str                  = Form(...),
    location:                str                  = Form(...),
    keep_image_ids:          Optional[List[int]]  = Form(default=None),
    images:           Annotated[Optional[List[UploadFile]], File()] = None,
) -> CreateOrUpdateUsedProductListingSchema:
    try:
        return CreateOrUpdateUsedProductListingSchema(
            used_product_listing_id = used_product_listing_id,
            name                    = name,
            description             = description,
            country                 = country,
            state                   = state,
            price                   = price,
            price_unit              = price_unit,
            location                = location,
            keep_image_ids          = keep_image_ids,
            images                  = images
        )
    except ValidationError as e:
        raise RequestValidationError(e.errors()) 
    
class UsedProductListingsSearchSuggestionsSchema(BaseModel):
    query: str

    @field_validator("query")
    def validate_query(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Query cannot be empty")
        return v
