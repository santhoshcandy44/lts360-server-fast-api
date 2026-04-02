from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ValidationError, field_validator, model_validator
from typing import Annotated, Optional, List, Literal
from fastapi import Form, UploadFile , File
import json

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

class CreateUsedProductListingSchema(BaseModel):
    name:                    str
    description:             str
    country:                 int
    state:                   int
    price:                   float
    price_unit:              str
    location:                str
    images:                  List[UploadFile]

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

    @field_validator("price")
    def validate_price(cls, v):
        if v < 0:
            raise ValueError("Price must be >= 0")
        return v

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
    def validate_images_and_keep(self):
        if not self.images:
            raise ValueError("At least 1 image is required")

        if self.images:
            for image in self.images:
                if image.content_type not in ALLOWED_TYPES:
                    raise ValueError(f"Invalid file type: {image.filename}")
                if image.size and image.size > MAX_IMAGE_SIZE:
                    raise ValueError(f"Image {image.filename} must be under 1MB")
        return self

async def create_used_product_listing_form(
    name:                    str                  = Form(...),
    description:             str                  = Form(...),
    country:                 int                  = Form(...),
    state:                   int                  = Form(...),
    price:                   float                = Form(...),
    price_unit:              str                  = Form(...),
    location:                str                  = Form(...),
    images:                  List[UploadFile]    =  File(...),
) -> CreateUsedProductListingSchema:
    try:
        return CreateUsedProductListingSchema(
            name                    = name,
            description             = description,
            country                 = country,
            state                   = state,
            price                   = price,
            price_unit              = price_unit,
            location                = location,
            images                  = images
        )
    except ValidationError as e:
        raise RequestValidationError(e.errors()) 
    
class UpdateUsedProductListingSchema(BaseModel):
    used_product_listing_id: int
    name:                    str
    description:             str
    price:                   float
    price_unit:              str
    keep_image_ids:          Optional[List[int]] = None
    images:                  Optional[List[UploadFile]] = None
    replace_image_ids:   Optional[List[int]]        = None
    replace_images:           Optional[List[UploadFile]] = None

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

    @field_validator("price")
    def validate_price(cls, v):
        if v < 0:
            raise ValueError("Price must be >= 0")
        return v

    @field_validator("keep_image_ids")
    def validate_keep_image_ids(cls, v):
        if v is None:
            return None
        if not isinstance(v, list):
            v = [v]
        return [int(i) for i in v]
     
    @model_validator(mode="after")
    def validate_images(self):
        has_kept_images = bool(self.keep_image_ids)
        has_replace_images = bool(self.replace_images)
        has_replace_ids = bool(self.replace_image_ids)

        if has_replace_images and not has_replace_ids:
            raise ValueError("replace_image_ids must be provided with replace_images")

        if has_replace_ids and not has_replace_images:
            raise ValueError("replace_images must be provided with replace_image_ids")

        if has_replace_images and has_replace_ids:
            if len(self.replace_images) != len(self.replace_image_ids):
                raise ValueError("replace_images and replace_image_ids must have the same length")

        if has_kept_images and has_replace_ids:
            overlap = set(self.keep_image_ids) & set(self.replace_image_ids)
            if overlap:
                raise ValueError(f"Image IDs cannot be in both keep_image_ids and replace_image_ids: {overlap}")

        for image in (self.images or []) + (self.replace_images or []):
            if image.content_type not in ALLOWED_TYPES:
                raise ValueError(f"Invalid file type: {image.filename}")
            if image.size and image.size > MAX_IMAGE_SIZE:
                raise ValueError(f"Image {image.filename} must be under 1MB")

        return self

async def update_used_product_listing_form(
    used_product_listing_id: int,
    name:                    str                  = Form(...),
    description:             str                  = Form(...),
    price:                   float                = Form(...),
    price_unit:              str                  = Form(...),
    keep_image_ids:   Optional[List[int]]       = Form(None),
    images:           Optional[List[UploadFile]] = File(None),
    replace_image_ids:   Optional[List[int]]       = Form(None),
    replace_images:           Optional[List[UploadFile]] = File(None),
) -> UpdateUsedProductListingSchema:
    try:
        return UpdateUsedProductListingSchema(
            used_product_listing_id = used_product_listing_id,
            name                    = name,
            description             = description,
            price                   = price,
            price_unit              = price_unit,
            keep_image_ids   = keep_image_ids,
            images           = images,
            replace_image_ids = replace_image_ids,
            replace_images = replace_images
        )
    except ValidationError as e:
        raise RequestValidationError(e.errors()) 
    
class PublishUsedProductListingStateOptionsSchema(BaseModel):
    country_id: int

    @field_validator("country_id")
    def validate_country_id(cls, v):
        if v <= 0:
            raise ValueError("Invalid country id format")
        return v
   
class UsedProductListingsSearchSuggestionsSchema(BaseModel):
    query: str

    @field_validator("query")
    def validate_query(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Query cannot be empty")
        return v
