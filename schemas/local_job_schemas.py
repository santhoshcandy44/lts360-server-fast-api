from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, ValidationError, field_validator, model_validator
from typing import Annotated, Optional, List
import json
from fastapi import File, Form, UploadFile

VALID_MARITAL_STATUSES = ['ANY', 'SINGLE', 'MARRIED', 'UNMARRIED', 'WIDOWED']
VALID_COUNTRIES        = ['IN']
VALID_INDIAN_STATES    = [
    "Andaman and Nicobar Islands", "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar",
    "Chandigarh", "Chhattisgarh", "Dadra and Nagar Haveli and Daman and Diu", "Delhi", "Goa",
    "Gujarat", "Haryana", "Himachal Pradesh", "Jammu and Kashmir", "Jharkhand", "Karnataka",
    "Kerala", "Ladakh", "Lakshadweep", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya",
    "Mizoram", "Nagaland", "Odisha", "Puducherry", "Punjab", "Rajasthan", "Sikkim", "Tamil Nadu",
    "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand", "West Bengal"
]

class GuestGetLocalJobsSchema(BaseModel):
    s:          Optional[str]   = None
    latitude:   Optional[float] = None
    longitude:  Optional[float] = None
    page_size:  Optional[int]   = None
    next_token: Optional[str]   = None

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

class GetLocalJobsbSchema(BaseModel):
    s:          Optional[str] = None
    page_size:  Optional[int] = None
    next_token: Optional[str] = None

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

class LocalJobIdSchema(BaseModel):
    local_job_id: int

    @field_validator("local_job_id")
    def validate_local_job_id(cls, v):
        if v <= 0:
            raise ValueError("Invalid local job id")
        return v    

class CreateOrUpdateLocalJobSchema(BaseModel):
    local_job_id:     int                        = -1
    title:            str
    description:      str
    company:          str
    age_min:          int
    age_max:          int
    salary_min:       int
    salary_max:       int
    salary_unit:      str
    marital_statuses: Optional[List[str]]        = []
    country:          str
    state:            str
    keep_image_ids:   Optional[List[int]]        = None
    location:         str
    images:           Optional[List[UploadFile]] = None

    @field_validator("title")
    def validate_title(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Title is required")
        if not 1 <= len(v) <= 100:
            raise ValueError("Title must be between 1 and 100 characters long")
        return v

    @field_validator("description")
    def validate_description(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Description is required")
        if not 1 <= len(v) <= 5000:
            raise ValueError("Description must be between 1 and 5000 characters long")
        return v

    @field_validator("company")
    def validate_company(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Company is required")
        if not 1 <= len(v) <= 100:
            raise ValueError("Company must be between 1 and 100 characters long")
        return v

    @field_validator("age_min")
    def validate_age_min(cls, v):
        if not 18 <= v <= 60:
            raise ValueError("Minimum age must be between 18 and 60")
        return v

    @field_validator("age_max")
    def validate_age_max(cls, v):
        if not 18 <= v <= 60:
            raise ValueError("Maximum age must be between 18 and 60")
        return v

    @field_validator("marital_statuses")
    def validate_marital_statuses(cls, v):
        if v is None:
            return []
        if not isinstance(v, list):
            v = [v]
        if not all(s in VALID_MARITAL_STATUSES for s in v):
            raise ValueError("Invalid marital status")
        return v

    @field_validator("country")
    def validate_country(cls, v):
        if v not in VALID_COUNTRIES:
            raise ValueError("Invalid country")
        return v

    @field_validator("keep_image_ids")
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
    def validate_age_range(self):
        if self.age_max < self.age_min:
            raise ValueError("Maximum age must be >= minimum age")
        return self

    @model_validator(mode="after")
    def validate_salary_range(self):
        if self.salary_max != -1 and self.salary_max < self.salary_min:
            raise ValueError("Maximum salary must be >= minimum salary")
        return self

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

async def create_or_update_local_job_form(
    title:            Annotated[str,                  Form(...)],
    description:      Annotated[str,                  Form(...)],
    company:          Annotated[str,                  Form(...)],
    age_min:          Annotated[int,                  Form(...)],
    age_max:          Annotated[int,                  Form(...)],
    salary_min:       Annotated[int,                  Form(...)],
    salary_max:       Annotated[int,                  Form(...)],
    salary_unit:      Annotated[str,                  Form(...)],
    country:          Annotated[str,                  Form(...)],
    state:            Annotated[str,                  Form(...)],
    location:         Annotated[str,                  Form(...)],
    local_job_id:     Annotated[int,                  Form()]    = -1,
    marital_statuses: Annotated[Optional[List[str]],  Form()]    = [],
    keep_image_ids:   Annotated[Optional[List[int]],  Form()]    = None,
    images:           Annotated[Optional[List[UploadFile]], File()] = None,
) -> CreateOrUpdateLocalJobSchema:
    try:
        return CreateOrUpdateLocalJobSchema(
            local_job_id     = local_job_id,
            title            = title,
            description      = description,
            company          = company,
            age_min          = age_min,
            age_max          = age_max,
            salary_min       = salary_min,
            salary_max       = salary_max,
            salary_unit      = salary_unit,
            marital_statuses = marital_statuses,
            country          = country,
            state            = state,
            keep_image_ids   = keep_image_ids,
            location         = location,
            images           = images,
        )
    except ValidationError as e:
        raise RequestValidationError(e.errors()) 
    
class GetPublishedLocalJobsSchema(BaseModel):
    page_size:  Optional[int] = 20
    next_token: Optional[str] = None

    @field_validator("page_size")
    def validate_page_size(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Page size must be a positive integer")
        return v
      
class GetLocalJobApplicationsSchema(BaseModel):
    local_job_id:   int
    page_size:  Optional[int] = None
    next_token: Optional[str] = None

    
    @field_validator("local_job_id")
    def validate_local_job_id(cls, v):
        if v <= 0:
            raise ValueError("Invalid local job id")
        return v

    @field_validator("page_size")
    def validate_page_size(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Page size must be a positive integer")
        return v

class LocalJobApplicationSchema(BaseModel):
    local_job_id:   int
    application_id: int

    @field_validator("local_job_id")
    def validate_local_job_id(cls, v):
        if v <= 0:
            raise ValueError("Invalid local job id")
        return v

    @field_validator("application_id")
    def validate_application_id(cls, v):
        if v <= 0:
            raise ValueError("Invalid application id")
        return v

class SearchSuggestionsSchema(BaseModel):
    query: str

    @field_validator("query")
    def validate_query(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Search query cannot be empty")
        return v
    

MAX_IMAGE_SIZE    = 1 * 1024 * 1024  
ALLOWED_TYPES     = ["image/jpeg", "image/png", "image/webp"]