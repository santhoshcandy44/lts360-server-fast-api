# schemas/local_job_schemas.py
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


class LocationSchema(BaseModel):
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


class CreateLocalJobRequest(BaseModel):
    title:            str
    description:      str
    company:          str
    age_min:          int
    age_max:          int
    salary_min:       int
    salary_max:       int
    salary_unit:      Literal["INR", "USD"]
    marital_statuses: List[Literal["ANY", "SINGLE", "MARRIED", "UNMARRIED", "WIDOWED"]]
    country:          Literal["IN"]
    state:            str
    location:         LocationSchema
    keep_image_ids:   Optional[List[int]] = None

    @field_validator("title")
    def validate_title(cls, v):
        if not 1 <= len(v) <= 100:
            raise ValueError("Title must be between 1 and 100 characters")
        return v.strip()

    @field_validator("description")
    def validate_description(cls, v):
        if not 1 <= len(v) <= 5000:
            raise ValueError("Description must be between 1 and 5000 characters")
        return v.strip()

    @field_validator("company")
    def validate_company(cls, v):
        if not 1 <= len(v) <= 100:
            raise ValueError("Company must be between 1 and 100 characters")
        return v.strip()

    @field_validator("age_min", "age_max")
    def validate_age(cls, v):
        if not 18 <= v <= 60:
            raise ValueError("Age must be between 18 and 60")
        return v

    @field_validator("state")
    def validate_state(cls, v):
        if v not in VALID_STATES_IN:
            raise ValueError("Invalid state for India")
        return v

    @model_validator(mode="after")
    def validate_age_range(self):
        if self.age_max < self.age_min:
            raise ValueError("Maximum age must be >= minimum age")
        return self

    @model_validator(mode="after")
    def validate_salary_range(self):
        if self.salary_max != -1 and self.salary_max < self.salary_min:
            raise ValueError("Maximum salary must be >= minimum salary")
        return self