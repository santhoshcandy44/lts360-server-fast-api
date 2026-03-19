# schemas/service_schemas.py
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


class PlanFeature(BaseModel):
    feature_name:  str
    feature_value: str

    @field_validator("feature_name")
    def validate_feature_name(cls, v):
        if len(v) > 40:
            raise ValueError("Feature name must have a maximum length of 40")
        return v

    @field_validator("feature_value")
    def validate_feature_value(cls, v):
        if len(v) > 10:
            raise ValueError("Feature value must have a maximum length of 10")
        return v


class PlanItem(BaseModel):
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
        if len(v) > 20:
            raise ValueError("Plan name cannot exceed 20 characters")
        return v

    @field_validator("plan_description")
    def validate_plan_description(cls, v):
        if len(v) > 500:
            raise ValueError("Plan description cannot exceed 500 characters")
        return v

    @field_validator("plan_features")
    def validate_plan_features(cls, v):
        if not 1 <= len(v) <= 10:
            raise ValueError("Plan features must be a non-empty array with max 10 features")
        return v


class ServiceLocationSchema(BaseModel):
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


class CreateServiceRequest(BaseModel):
    title:             str
    short_description: str
    long_description:  str
    industry:          int
    country:           Literal["IN"]
    state:             str
    plans:             List[PlanItem]
    location:          ServiceLocationSchema
    keep_image_ids:    Optional[List[int]] = None

    @field_validator("title")
    def validate_title(cls, v):
        if not 1 <= len(v) <= 100:
            raise ValueError("Title must be between 1 and 100 characters")
        return v.strip()

    @field_validator("short_description")
    def validate_short_description(cls, v):
        if not 1 <= len(v) <= 250:
            raise ValueError("Short description must be between 1 and 250 characters")
        return v.strip()

    @field_validator("long_description")
    def validate_long_description(cls, v):
        if not 1 <= len(v) <= 5000:
            raise ValueError("Long description must be between 1 and 5000 characters")
        return v.strip()

    @field_validator("state")
    def validate_state(cls, v):
        if v not in VALID_STATES_IN:
            raise ValueError("State must be a valid state of India")
        return v

    @field_validator("plans")
    def validate_plans(cls, v):
        if not 1 <= len(v) <= 3:
            raise ValueError("Plans must be 1-3 array")
        return v


class UpdateServiceInfoRequest(BaseModel):
    title:             str
    short_description: str
    long_description:  str
    industry:          int

    @field_validator("title")
    def validate_title(cls, v):
        if not 1 <= len(v) <= 100:
            raise ValueError("Title must be between 1 and 100 characters")
        return v.strip()

    @field_validator("short_description")
    def validate_short_description(cls, v):
        if not 1 <= len(v) <= 250:
            raise ValueError("Short description must be between 1 and 250 characters")
        return v.strip()

    @field_validator("long_description")
    def validate_long_description(cls, v):
        if not 1 <= len(v) <= 5000:
            raise ValueError("Long description must be between 1 and 5000 characters")
        return v.strip()


class UpdateServicePlansRequest(BaseModel):
    plans: List[PlanItem]

    @field_validator("plans")
    def validate_plans(cls, v):
        if not 1 <= len(v) <= 3:
            raise ValueError("Plans must be 1-3 array")
        return v


class UpdateServiceImagesRequest(BaseModel):
    keep_image_ids: Optional[List[int]] = None


class UpdateServiceLocationRequest(BaseModel):
    latitude:      float
    longitude:     float
    geo:           str
    location_type: Literal["approximate", "precise"]

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


class UpdateIndustriesRequest(BaseModel):
    industries: str