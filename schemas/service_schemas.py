from pydantic import BaseModel, field_validator, model_validator
from typing import Optional, List, Literal
from fastapi import Form, UploadFile, File
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


# ──────────────────────────────────────────────
# Shared sub-models
# ──────────────────────────────────────────────

class PlanFeature(BaseModel):
    feature_name:  str
    feature_value: str

    @field_validator("feature_name")
    def validate_feature_name(cls, v):
        if not isinstance(v, str):
            raise ValueError("Feature name must be a string")
        if len(v) > 40:
            raise ValueError("Feature name must have a maximum length of 40")
        return v

    @field_validator("feature_value")
    def validate_feature_value(cls, v):
        if not isinstance(v, str):
            raise ValueError("Feature value must be a string")
        if len(v) > 10:
            raise ValueError("Feature value must have a maximum length of 10")
        return v


class Plan(BaseModel):
    plan_id:            int
    plan_name:          str
    plan_description:   str
    plan_price:         float
    price_unit:         Literal["INR", "USD"]
    plan_delivery_time: int
    duration_unit:      Literal["HR", "D", "W", "M"]
    plan_features:      List[PlanFeature]

    @field_validator("plan_name")
    def validate_plan_name(cls, v):
        if not isinstance(v, str):
            raise ValueError("Plan name must be a string")
        if len(v) > 20:
            raise ValueError("Plan name cannot exceed 20 characters")
        return v

    @field_validator("plan_description")
    def validate_plan_description(cls, v):
        if not isinstance(v, str):
            raise ValueError("Plan description must be a string")
        if len(v) > 500:
            raise ValueError("Plan description cannot exceed 500 characters")
        return v

    @field_validator("plan_features")
    def validate_plan_features(cls, v):
        if not 1 <= len(v) <= 10:
            raise ValueError("Plan features must be a non-empty array with max 10 features")
        return v


# ──────────────────────────────────────────────
# Path param models
# ──────────────────────────────────────────────

class ServiceIdParam(BaseModel):
    service_id: int

    @field_validator("service_id")
    def validate_service_id(cls, v):
        if v <= 0:
            raise ValueError("Invalid service id format")
        return v


class UserIdParam(BaseModel):
    user_id: int

    @field_validator("user_id")
    def validate_user_id(cls, v):
        if v <= 0:
            raise ValueError("Invalid user id format")
        return v


# ──────────────────────────────────────────────
# Query param models
# ──────────────────────────────────────────────

class GuestGetServicesRequest(BaseModel):
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


class GetServicesRequest(BaseModel):
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


class GetMeServicesRequest(BaseModel):
    page_size:      Optional[int] = None
    next_token:     Optional[str] = None
    previous_token: Optional[str] = None

    @field_validator("page_size")
    def validate_page_size(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Invalid page size format")
        return v


class GetUserProfileServicesRequest(BaseModel):
    page_size: Optional[int] = None

    @field_validator("page_size")
    def validate_page_size(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Invalid page size format")
        return v


class GetServicesByUserIdRequest(BaseModel):
    page_size:      Optional[int] = None
    next_token:     Optional[str] = None
    previous_token: Optional[str] = None

    @field_validator("page_size")
    def validate_page_size(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Invalid page size format")
        return v


class SearchSuggestionsRequest(BaseModel):
    query: str

    @field_validator("query")
    def validate_query(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Query cannot be empty")
        return v


# ──────────────────────────────────────────────
# Body models
# ──────────────────────────────────────────────

class CreateServiceRequest(BaseModel):
    title:             str
    short_description: str
    long_description:  str
    industry:          int
    country:           str
    state:             str
    plans:             str
    location:          str

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

    @field_validator("country")
    def validate_country(cls, v):
        if v not in VALID_COUNTRIES:
            raise ValueError("Country must be a valid country (IN)")
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
        return v

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
        return v

    @model_validator(mode="after")
    def validate_state(self):
        if self.country == "IN" and self.state not in VALID_INDIAN_STATES:
            raise ValueError("State must be a valid state of India")
        return self


async def create_service_form(
    title:             str                  = Form(...),
    short_description: str                  = Form(...),
    long_description:  str                  = Form(...),
    industry:          int                  = Form(...),
    country:           str                  = Form(...),
    state:             str                  = Form(...),
    plans:             str                  = Form(...),
    location:          str                  = Form(...),
) -> CreateServiceRequest:
    return CreateServiceRequest(
        title             = title,
        short_description = short_description,
        long_description  = long_description,
        industry          = industry,
        country           = country,
        state             = state,
        plans             = plans,
        location          = location,
    )


class UpdateServiceInfoRequest(BaseModel):
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


class UpdateServiceThumbnailRequest(BaseModel):
    image_id: int

    @field_validator("image_id")
    def validate_image_id(cls, v):
        if not isinstance(v, int):
            raise ValueError("Image ID must be a valid integer")
        return v


class UpdateServiceImagesRequest(BaseModel):
    keep_image_ids: Optional[List[int]] = None

    @field_validator("keep_image_ids", mode="before")
    def validate_keep_image_ids(cls, v):
        if v is None:
            return None
        if not isinstance(v, list):
            v = [v]
        result = []
        for id in v:
            n = int(id)
            result.append(n)
        return result


async def update_service_images_form(
    keep_image_ids: Optional[List[int]] = Form(default=None),
) -> UpdateServiceImagesRequest:
    return UpdateServiceImagesRequest(
        keep_image_ids = keep_image_ids,
    )


class UpdateServicePlansRequest(BaseModel):
    plans: str

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
        return v


class UpdateServiceLocationRequest(BaseModel):
    latitude:      float
    longitude:     float
    geo:           str
    location_type: str

    @field_validator("latitude")
    def validate_latitude(cls, v):
        if not -90 <= v <= 90:
            raise ValueError("Latitude must be a valid float between -90 and 90")
        return v

    @field_validator("longitude")
    def validate_longitude(cls, v):
        if not -180 <= v <= 180:
            raise ValueError("Longitude must be a valid float between -180 and 180")
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


class UpdateIndustriesRequest(BaseModel):
    industries: str

    @field_validator("industries")
    def validate_industries(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Industries cannot be empty")
        return v

class UpdateIndustriesRequest(BaseModel):
    industries: str