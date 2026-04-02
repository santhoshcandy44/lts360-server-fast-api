from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ValidationError, field_validator, model_validator
from typing import Annotated, Optional, List, Literal
from fastapi import Form, Query, UploadFile, File
import json

VALID_COUNTRIES     = ['IN']
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


class GuestGetServicesSchema(BaseModel):
    s:              Optional[str]        = None
    latitude:       Optional[float]      = None
    longitude:      Optional[float]      = None
    industries:     Optional[List[int]]  = None 
    page_size:      Optional[int]        = None
    next_token:     Optional[str]        = None
    previous_token: Optional[str]        = None

    @field_validator("s")
    def validate_s(cls, v):
        if v is not None:
            v = v.strip()
            if len(v) > 100:
                raise ValueError("Query string must be between 1 and 100 characters long")
        return v

    @field_validator("latitude")
    def validate_latitude(cls, v):
        if v is not None and not -90 <= v <= 90:
            raise ValueError("Latitude must be a valid float between -90 and 90")
        return v

    @field_validator("longitude")
    def validate_longitude(cls, v):
        if v is not None and not -180 <= v <= 180:
            raise ValueError("Longitude must be a valid float between -180 and 180")
        return v

    @field_validator("industries")
    def validate_industries(cls, v):
        if v is not None:
            if not all(isinstance(i, int) and i > 0 for i in v):
                raise ValueError("Each industry ID must be a positive integer")
        return v

    @field_validator("page_size")
    def validate_page_size(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Invalid page size format")
        return v


def create_guest_get_services_params(
        s:          Optional[str]   = Query(default=None),
        latitude:   Optional[float] = Query(default=None),
        longitude:  Optional[float] = Query(default=None),
        page_size:  int             = Query(default=20),
        next_token: Optional[str]   = Query(default=None),
        industries: Optional[List[int]] = Query(default=None), 
):
    try:
        return GuestGetServicesSchema(
            s= s,
            latitude=latitude,
            longitude=longitude,
            page_size=page_size,
            next_token=next_token,
            industries=industries
        ) 
    except ValidationError as e:
        raise RequestValidationError(e.errors())           

class GetServicesSchema(BaseModel):
    s:              Optional[str] = None
    page_size:      Optional[int] = None
    next_token:     Optional[str] = None
    previous_token: Optional[str] = None

    @field_validator("s")
    def validate_s(cls, v):
        if v is not None:
            v = v.strip()
            if len(v) > 100:
                raise ValueError("Query string must be between 1 and 100 characters long")
        return v

    @field_validator("page_size")
    def validate_page_size(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Invalid page size format")
        return v

class ServiceIdSchema(BaseModel):
    service_id: int

    @field_validator("service_id")
    def validate_service_id(cls, v):
        if v <= 0:
            raise ValueError("Invalid service id format")
        return v

class GetUserProfileServicesSchema(BaseModel):
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
            raise ValueError("Invalid page size format")
        return v

class GetServicesByUserIdSchema(BaseModel):
    user_id: int
    page_size:      Optional[int] = None
    next_token:     Optional[str] = None
    previous_token: Optional[str] = None

    @field_validator("user_id")
    def validate_user_id(cls, v):
        if v <= 0:
            raise ValueError("Invalid user id")
        return v
    
    @field_validator("page_size")
    def validate_page_size(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Invalid page size format")
        return v

class CreateServiceSchema(BaseModel):
    title:             str
    short_description: str
    long_description:  str
    industry:          int
    country:           int
    state:             int
    plans:             str
    location:          str
    images:            List[UploadFile] = None
    thumbnail:         UploadFile= None

    @field_validator("title")
    def validate_title(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Title cannot be empty")
        if not 1 <= len(v) <= 100:
            raise ValueError("Title must be between 1 and 100 characters")
        return v

    @field_validator("short_description")
    def validate_short_description(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Short Description cannot be empty")
        if not 1 <= len(v) <= 250:
            raise ValueError("Short Description must be between 1 and 250 characters")
        return v

    @field_validator("long_description")
    def validate_long_description(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Long Description cannot be empty")
        if not 1 <= len(v) <= 5000:
            raise ValueError("Long Description must be between 1 and 5000 characters")
        return v
    
    @field_validator("industry")
    def validate_industry(cls, v):
        if v <= 0:
            raise ValueError("Invalid industry")
        return v

    @field_validator("plans")
    def validate_plans(cls, v):
        try:
            parsed = json.loads(v)
        except Exception:
            raise ValueError("Plans must be a valid JSON array")
        if not isinstance(parsed, list) or not 1 <= len(parsed) <= 3:
            raise ValueError("Plans must be 1-3 array")
        for plan in parsed:
            if not isinstance(plan, dict):
                raise ValueError("Each plan must be an object")
        return parsed

    @field_validator("location")
    def validate_location(cls, v):
        try:
            parsed = json.loads(v)
        except Exception:
            raise ValueError("Location must be an object")
        if not isinstance(parsed, dict):
            raise ValueError("Location must be an object")
        lat = parsed.get("latitude")
        lng = parsed.get("longitude")
        if lat is None:
            raise ValueError("Latitude is required")
        if lng is None:
            raise ValueError("Longitude is required")
        if not -90 <= float(lat) <= 90:
            raise ValueError("Latitude must be a number between -90 and 90")
        if not -180 <= float(lng) <= 180:
            raise ValueError("Longitude must be a number between -180 and 180")
        return parsed

    @model_validator(mode="after")
    def validate_state(self):
        if self.country == "IN" and self.state not in VALID_INDIAN_STATES:
            raise ValueError("State must be a valid state of India")
        return self

    @model_validator(mode="after")
    def validate_thumbnail(self):
        if not self.thumbnail:
            raise ValueError("Thumbnail is required")

        if self.thumbnail:
            if self.thumbnail.content_type not in ALLOWED_TYPES:
                raise ValueError(f"Invalid file type: {self.thumbnail.filename}")
            if self.thumbnail.size and self.thumbnail.size > MAX_IMAGE_SIZE:
                raise ValueError(f"Thumbnail must be under 1MB")
        return self
    
    @model_validator(mode="after")
    def validate_images(self):
        if not self.images:
            raise ValueError("At least 1 image is required")
        if self.images:
            for image in self.images:
                if image.content_type not in ALLOWED_TYPES:
                    raise ValueError(f"Invalid file type: {image.filename}")
                if image.size and image.size > MAX_IMAGE_SIZE:
                    raise ValueError(f"Image {image.filename} must be under 1MB")
        return self

class PlanFeature(BaseModel):
    name:  str
    value: str

    @field_validator("name")
    def validate_feature_name(cls, v):
        if not isinstance(v, str):
            raise ValueError("Feature name must be a string")
        if len(v) > 40:
            raise ValueError("Feature name must have a maximum length of 40")
        return v

    @field_validator("value")
    def validate_feature_value(cls, v):
        if not isinstance(v, str):
            raise ValueError("Feature value must be a string")
        if len(v) > 10:
            raise ValueError("Feature value must have a maximum length of 10")
        return v

class Plan(BaseModel):
    plan_id:       int = -1
    name:          str
    description:   str
    price:    float
    price_unit:    Literal["INR", "USD"]
    delivery_time: int
    duration_unit: Literal["HR", "D", "W", "M"]
    features: List[PlanFeature]

    @field_validator("name")
    def validate_name(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Plan name cannot be empty")
        if len(v) > 20:
            raise ValueError("Plan name cannot exceed 20 characters")
        return v

    @field_validator("description")
    def validate_description(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Plan description cannot be empty")
        if len(v) > 500:
            raise ValueError("Plan description cannot exceed 500 characters")
        return v

    @field_validator("price")
    def validate_price(cls, v):
        if v <= 0:
            raise ValueError("Plan price must be greater than 0")
        return v

    @field_validator("delivery_time")
    def validate_delivery_time(cls, v):
        if v <= 0:
            raise ValueError("Plan delivery time must be greater than 0")
        return v

    @field_validator("features")
    def validate_features(cls, v):
        if not 1 <= len(v) <= 10:
            raise ValueError("Plan must have between 1 and 10 features")
        return v
    
async def create_service_form(
    title:             str                  = Form(...),
    short_description: str                  = Form(...),
    long_description:  str                  = Form(...),
    industry:          int                  = Form(...),
    country:           int                  = Form(...),
    state:             int                  = Form(...),
    plans:             str                  = Form(...),
    location:          str                  = Form(...),
    images:            List[UploadFile]     = Form(...),
    thumbnail:         UploadFile           = Form(...)
) -> CreateServiceSchema:
    try:
        return CreateServiceSchema(
        title             = title,
        short_description = short_description,
        long_description  = long_description,
        industry          = industry,
        country           = country,
        state             = state,
        plans             = plans,
        location          = location,
        images            = images,
        thumbnail         = thumbnail
    )
    except ValidationError as e:
        raise RequestValidationError(e.errors())     

class GetPublishedServicesSchema(BaseModel):
    page_size:      Optional[int] = None
    next_token:     Optional[str] = None
    previous_token: Optional[str] = None

    @field_validator("page_size")
    def validate_page_size(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Invalid page size format")
        return v

class UpdateServiceInfoSchema(BaseModel):
    service_id:        int
    title:             str
    short_description: str
    long_description:  str
    industry:          int

    @field_validator("title")
    def validate_title(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Title cannot be empty")
        if not 1 <= len(v) <= 100:
            raise ValueError("Title must be between 1 and 100 characters")
        return v

    @field_validator("short_description")
    def validate_short_description(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Short Description cannot be empty")
        if not 1 <= len(v) <= 250:
            raise ValueError("Short Description must be between 1 and 250 characters")
        return v

    @field_validator("long_description")
    def validate_long_description(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Long Description cannot be empty")
        if not 1 <= len(v) <= 5000:
            raise ValueError("Long Description must be between 1 and 5000 characters")
        return v
    
    @field_validator("industry")
    def validate_industry(cls, v):
        if v <= 0:
            raise ValueError("Invalid industry")
        return v

class UpdateServiceThumbnailSchema(BaseModel):
    service_id: int
    thumbnail_id: int
    thumbnail:    UploadFile= None

    @field_validator("service_id")
    def validate_service_id(cls, v):
        if v <= 0:
            raise ValueError("Invalid service id format")
        return v

    @field_validator("thumbnail_id")
    def validate_image_id(cls, v):
        if not isinstance(v, int):
            raise ValueError("Thumbnail ID must be a valid integer")
        return v
    
    @model_validator(mode="after")
    def validate_thumbnail(self):
        if not self.thumbnail:
            raise ValueError("Thumbnail is required")

        if self.thumbnail:
            if self.thumbnail.content_type not in ALLOWED_TYPES:
                raise ValueError(f"Invalid file type: {self.thumbnail.filename}")
            if self.thumbnail.size and self.thumbnail.size > MAX_IMAGE_SIZE:
                raise ValueError(f"Thumbnail must be under 1MB")
        return self

async def update_thumbnail_form(
    service_id: int,    
    thumbnail_id:            Annotated[int, Form(...)],
    thumbnail:           Annotated[Optional[UploadFile], File()] = None,
) -> UpdateServiceThumbnailSchema:
    try:
        return UpdateServiceThumbnailSchema(
            service_id          = service_id,
            thumbnail_id        = thumbnail_id,
            thumbnail           = thumbnail,
        )
    except ValidationError as e:
        raise RequestValidationError(e.errors()) 

class UpdateServiceImagesSchema(BaseModel):
    service_id: int
    keep_image_ids:          Optional[List[int]] = None
    images:                  Optional[List[UploadFile]] = None
    replace_image_ids:   Optional[List[int]]        = None
    replace_images:           Optional[List[UploadFile]] = None

    @field_validator("service_id")
    def validate_service_id(cls, v):
        if v <= 0:
            raise ValueError("Invalid service id format")
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

async def update_service_images_form(
    service_id: int,
    keep_image_ids: Annotated[List[int], Form(...)],
    images:           Annotated[List[UploadFile], File()] = None,
) -> UpdateServiceImagesSchema:
    try:
        return UpdateServiceImagesSchema(
            service_id          = service_id,
            keep_image_ids      = keep_image_ids,
            images              = images,
        )
    except ValidationError as e:
        raise RequestValidationError(e.errors())
    
class UpdateServicePlansSchema(BaseModel):
    service_id: int = 0
    plans: List[Plan]

    @field_validator("plans")
    def validate_plans(cls, v):
        if len(v) < 1:
            raise ValueError("At least 1 plan is required")
        if len(v) > 3:
            raise ValueError("Maximum 3 plans allowed")
        return v

class PublishServiceStateOptionsSchema(BaseModel):
    country_id: int

    @field_validator("country_id")
    def validate_country_id(cls, v):
        if v <= 0:
            raise ValueError("Invalid country id format")
        return v

class UpdateIndustriesSchema(BaseModel):
    industries: List[int]

    @field_validator("industries")
    def validate_industries(cls, v):
        if not v:
            raise ValueError("At least 1 industry is required")
        return v
    
class ServiceSearchSuggestionsSchema(BaseModel):
    query: str

    @field_validator("query")
    def validate_query(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Query cannot be empty")
        return v
