import datetime
from datetime import datetime,  date

from typing import List, Optional
from fastapi import Form, Query, UploadFile
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, EmailStr, ValidationError, field_validator, model_validator

class GoogleLoginSchema(BaseModel):
    id_token: str

    @field_validator("id_token")
    @classmethod
    def validate_id_token(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("ID token is required")
        return v


class EmailLoginSchema(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if len(v) > 254:
            raise ValueError("Email must be at most 254 characters")
        return v.lower().strip()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Password is required")
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        if len(v) > 128:
            raise ValueError("Password must be at most 128 characters")
        return v


VALID_DURATIONS = {"1", "7", "30", "90", "custom"}

class DashboardSchema(BaseModel):
    duration: str = "7"
    start_date: Optional[str] = None
    end_date: Optional[str] = None

    @field_validator("duration")
    @classmethod
    def validate_duration(cls, v: str) -> str:
        v = v.strip()
        if v not in VALID_DURATIONS:
            raise ValueError(f"duration must be one of {VALID_DURATIONS}")
        return v

    @field_validator("start_date", "end_date")
    @classmethod
    def validate_date_format(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format")
        return v

    @model_validator(mode="after")
    def validate_custom_range(self) -> "DashboardSchema":
        if self.duration == "custom":
            if not self.start_date or not self.end_date:
                raise ValueError("start_date and end_date are required when duration is 'custom'")
            if self.start_date > self.end_date:
                raise ValueError("start_date must be before end_date")
        return self

class SearchQuerySchema(BaseModel):
    q: str = ""

    @field_validator("q")
    @classmethod
    def validate_q(cls, v: str) -> str:
        v = v.strip()
        if len(v) > 100:
            raise ValueError("Search query must be at most 100 characters")
        return v

class SearchQuerySchema(BaseModel):
    q: str = ""

    @field_validator("q")
    @classmethod
    def validate_q(cls, v: str) -> str:
        v = v.strip()
        if len(v) > 100:
            raise ValueError("Search query must be at most 100 characters")
        return v

class StatesSearchSchema(BaseModel):
    q: str = ""
    country_id: Optional[int] = None

    @field_validator("q")
    @classmethod
    def validate_q(cls, v: str) -> str:
        v = v.strip()
        if len(v) > 100:
            raise ValueError("Search query must be at most 100 characters")
        return v

    @field_validator("country_id")
    @classmethod
    def validate_country_id(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 1:
            raise ValueError("country_id must be a positive integer")
        return v

class LocationsSearchSchema(BaseModel):
    q: str = ""
    state_id: Optional[int] = None
    country_id: Optional[int] = None

    @field_validator("q")
    @classmethod
    def validate_q(cls, v: str) -> str:
        v = v.strip()
        if len(v) > 100:
            raise ValueError("Search query must be at most 100 characters")
        return v

    @field_validator("state_id", "country_id")
    @classmethod
    def validate_ids(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v < 1:
            raise ValueError("ID must be a positive integer")
        return v

class PageSchema(BaseModel):
    page: int = 1

    @field_validator("page")
    @classmethod
    def validate_page(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Page must be at least 1")
        return v

class ApplicationsByJobSchema(BaseModel):
    job_id: int
    page: int = 1
    
    @field_validator("job_id")
    @classmethod
    def validate_job_id(cls, v: int) -> int:
        if v < 1:
            raise ValueError("job_id must be a positive integer")
        return v
    
    @field_validator("page")
    @classmethod
    def validate_page(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Page must be at least 1")
        return v  


class ManageApplicationSchema(BaseModel):
    job_id: int
    application_id: int = 1
    
    @field_validator("job_id")
    @classmethod
    def validate_job_id(cls, v: int) -> int:
        if v < 1:
            raise ValueError("job_id must be a positive integer")
        return v
    
    @field_validator("application_id")
    @classmethod
    def validate_page(cls, v: int) -> int:
        if v < 1:
            raise ValueError("application_id must be a positive integer")
        return v         

VALID_EXPERIENCE_FILTERS = {"Entry Level", "Mid Level", "Senior Level", "Executive"}

class JobListingsFilterSchema(BaseModel):
    page: int = 1
    experience: Optional[str] = None
    work_mode: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None

    @field_validator("page")
    @classmethod
    def validate_page(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Page must be at least 1")
        return v

    @field_validator("experience")
    @classmethod
    def validate_experience(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        if v not in VALID_EXPERIENCE_FILTERS:
            raise ValueError(f"experience must be one of {VALID_EXPERIENCE_FILTERS}")
        return v

    @field_validator("work_mode")
    @classmethod
    def validate_work_mode(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip().lower()
        if v not in VALID_WORK_MODES:
            raise ValueError(f"work_mode must be one of {VALID_WORK_MODES}")
        return v

    @field_validator("date_from", "date_to")
    @classmethod
    def validate_date_format(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format")
        return v

    @model_validator(mode="after")
    def validate_date_range(self) -> "JobListingsFilterSchema":
        if self.date_from and self.date_to:
            if self.date_from > self.date_to:
                raise ValueError("date_from must be before date_to")
        if (self.date_from and not self.date_to) or (self.date_to and not self.date_from):
            raise ValueError("Both date_from and date_to are required together")
        return self

VALID_WORK_MODES       = {"remote", "office", "hybrid", "flexible"}
VALID_EXPERIENCE_TYPES = {"fresher", "min_max", "fixed"}
VALID_EMPLOYMENT_TYPES = {"full_time", "part_time", "contract", "internship"}

class JobCreateSchema(BaseModel):
    title: str
    work_mode: str
    location: Optional[int] = None
    description: str
    experience_type: str
    experience_range_min: int = 0
    experience_range_max: int = 0
    experience_fixed: int = 0
    salary_min: float = 0
    salary_max: float = 0
    salary_not_disclosed: bool = False
    employment_type: str
    education: Optional[str] = None
    industry: Optional[str] = None
    department: Optional[str] = None
    role: Optional[str] = None
    must_have_skills: List[str] = []
    good_to_have_skills: List[str] = []
    vacancies: int = 1
    highlights: List[str] = []
    expiry_date: Optional[date] = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Title is required")
        if len(v) < 3:
            raise ValueError("Title must be at least 3 characters")
        if len(v) > 100:
            raise ValueError("Title must be at most 100 characters")
        return v

    @field_validator("description")
    @classmethod
    def validate_description(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Description is required")
        if len(v) < 10:
            raise ValueError("Description must be at least 10 characters")
        return v

    @field_validator("work_mode")
    @classmethod
    def validate_work_mode(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in VALID_WORK_MODES:
            raise ValueError(f"work_mode must be one of {VALID_WORK_MODES}")
        return v

    @field_validator("experience_type")
    @classmethod
    def validate_experience_type(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in VALID_EXPERIENCE_TYPES:
            raise ValueError(f"experience_type must be one of {VALID_EXPERIENCE_TYPES}")
        return v

    @field_validator("experience_range_min", "experience_range_max", "experience_fixed")
    @classmethod
    def validate_experience_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Experience values must be non-negative")
        return v

    @field_validator("experience_range_max")
    @classmethod
    def validate_experience_range(cls, v: int, info) -> int:
        min_val = info.data.get("experience_range_min", 0)
        if v < min_val:
            raise ValueError("experience_range_max must be >= experience_range_min")
        return v

    @field_validator("salary_min", "salary_max")
    @classmethod
    def validate_salary_non_negative(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Salary values must be non-negative")
        return v

    @field_validator("salary_max")
    @classmethod
    def validate_salary_range(cls, v: float, info) -> float:
        min_val = info.data.get("salary_min", 0)
        if v < min_val:
            raise ValueError("salary_max must be >= salary_min")
        return v

    @field_validator("employment_type")
    @classmethod
    def validate_employment_type(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in VALID_EMPLOYMENT_TYPES:
            raise ValueError(f"employment_type must be one of {VALID_EMPLOYMENT_TYPES}")
        return v

    @field_validator("vacancies")
    @classmethod
    def validate_vacancies(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Vacancies must be at least 1")
        if v > 1000:
            raise ValueError("Vacancies must be at most 1000")
        return v

    @field_validator("must_have_skills", "good_to_have_skills")
    @classmethod
    def validate_skills(cls, v: List[str]) -> List[str]:
        if len(v) > 20:
            raise ValueError("Cannot add more than 20 skills")
        return [s.strip() for s in v if s.strip()]

    @field_validator("highlights")
    @classmethod
    def validate_highlights(cls, v: List[str]) -> List[str]:
        if len(v) > 10:
            raise ValueError("Cannot add more than 10 highlights")
        return [h.strip() for h in v if h.strip()]

    @field_validator("expiry_date")
    @classmethod
    def validate_expiry_date(cls, v: Optional[date]) -> Optional[date]:
        if v and v < date.today():
            raise ValueError("Expiry date must be in the future")
        return v

class JobIdSchema(BaseModel):
    job_id: int

    @field_validator("job_id")
    @classmethod
    def validate_job_id(cls, v: int) -> int:
        if v < 1:
            raise ValueError("job_id must be a positive integer")
        return v

class StatusSchema(BaseModel):
    job_id: int
    action: str

    @field_validator("job_id")
    @classmethod
    def validate_job_id(cls, v: int) -> int:
        if v < 1:
            raise ValueError("job_id must be a positive integer")
        return v

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in {"publish", "draft"}:
            raise ValueError("action must be either 'publish' or 'draft'")
        return v

class ExtendSchema(BaseModel):
    job_id: int
    new_expiry_date: date

    @field_validator("job_id")
    @classmethod
    def validate_job_id(cls, v: int) -> int:
        if v < 1:
            raise ValueError("job_id must be a positive integer")
        return v

    @field_validator("new_expiry_date")
    @classmethod
    def validate_new_expiry_date(cls, v: date) -> date:
        if v < date.today():
            raise ValueError("New expiry date must be in the future")
        return v

STATUS_WORKFLOW = [
    {"id": "applied",   "label": "Applied",   "order": 1},
    {"id": "viewed",    "label": "Viewed",    "order": 2},
    {"id": "reviewed",  "label": "Reviewed",  "order": 3},
    {"id": "interview", "label": "Interview", "order": 4},
    {"id": "offer",     "label": "Offer",     "order": 5},
    {"id": "hired",     "label": "Hired",     "order": 6},
]

VALID_STATUSES = {s["id"] for s in STATUS_WORKFLOW}

class UpdateStatusSchema(BaseModel):
    job_id: int
    application_id: int = 1
         
    status: str

    @field_validator("job_id")
    @classmethod
    def validate_job_id(cls, v: int) -> int:
        if v < 1:
            raise ValueError("job_id must be a positive integer")
        return v
    
    @field_validator("application_id")
    @classmethod
    def validate_page(cls, v: int) -> int:
        if v < 1:
            raise ValueError("application_id must be a positive integer")
        return v    

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        v = v.strip().lower()
        if v not in VALID_STATUSES:
            raise ValueError(f"status must be one of {VALID_STATUSES}")
        return v

ALLOWED_LOGO_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_LOGO_SIZE = 1 * 1024 * 1024 

class OrganizationProfileSchema(BaseModel):
    organization_name: str
    email: str
    website: str
    organization_address: str
    country: Optional[int] = None
    state: Optional[int] = None
    location: Optional[int] = None
    postal_code: str = ""

    logo: Optional[UploadFile]

    @field_validator("organization_name")
    def validate_organization_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Organization name is required")
        if len(v) < 2:
            raise ValueError("Organization name must be at least 2 characters")
        if len(v) > 255:
            raise ValueError("Organization name must be at most 255 characters")
        return v

    @field_validator("email")
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not v:
            raise ValueError("Email is required")
        if len(v) > 254:
            raise ValueError("Email must be at most 254 characters")
        if "@" not in v:
            raise ValueError("Invalid email address")
        return v

    @field_validator("website")
    def validate_website(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Website is required")
        if not v.startswith(("http://", "https://")):
            raise ValueError("Website must start with http:// or https://")
        if len(v) > 200:
            raise ValueError("Website must be at most 200 characters")
        return v

    @field_validator("organization_address")
    def validate_address(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Address is required")
        if len(v) > 255:
            raise ValueError("Address must be at most 255 characters")
        return v

    @field_validator("postal_code")
    def validate_postal_code(cls, v: str) -> str:
        v = v.strip()
        if len(v) > 10:
            raise ValueError("Postal code must be at most 10 characters")
        return v
    
    @field_validator("logo")
    def validate_logo(cls, v: UploadFile):
        if v is None:
            return v
        if v.content_type not in ALLOWED_LOGO_TYPES:
            raise ValueError("Logo must be JPG, PNG or WebP")
        if v.size and v.size > MAX_LOGO_SIZE:
            raise ValueError("Logo must be smaller than 1MB")
        return v

def create_organization_profile_form(
    organization_name: str = Form(...),
    email: str = Form(...),
    website: str = Form(...),
    organization_address: str = Form(...),
    country: Optional[int] = Form(default=None),
    state: Optional[int] = Form(default=None),
    location: Optional[int] = Form(default=None),
    postal_code: str = Form(default=""),
) -> OrganizationProfileSchema:
    try:
        return OrganizationProfileSchema(
            organization_name=organization_name,
            email=email,
            website=website,
            organization_address=organization_address,
            country=country,
            state=state,
            location=location,
            postal_code=postal_code,
        )
    except ValidationError as e:
        raise RequestValidationError(e.errors())

ALLOWED_PROFILE_PIC_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_PROFILE_PIC_SIZE = 1 * 1024 * 1024 

class RecruiterProfileSchema(BaseModel):
    first_name: str
    last_name: Optional[str] = ""
    company: str
    role: str
    years_of_experience: int = 0
    bio: str = ""

    profile_pic: Optional[UploadFile]

    @field_validator("first_name")
    @classmethod
    def validate_first_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("First name is required")
        if len(v) < 2:
            raise ValueError("First name must be at least 2 characters")
        if len(v) > 100:
            raise ValueError("First name must be at most 100 characters")
        return v

    @field_validator("last_name")
    @classmethod
    def validate_last_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return ""
        v = v.strip()
        if len(v) > 100:
            raise ValueError("Last name must be at most 100 characters")
        return v

    @field_validator("company")
    @classmethod
    def validate_company(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Company is required")
        if len(v) > 50:
            raise ValueError("Company must be at most 50 characters")
        return v

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        v = v.strip()
        valid_roles = {"RECRUITER", "HIRING_MANAGER", "TALENT_ACQUISITION", "HR"}
        if v not in valid_roles:
            raise ValueError(f"role must be one of {valid_roles}")
        return v

    @field_validator("years_of_experience")
    @classmethod
    def validate_years_of_experience(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Years of experience must be non-negative")
        if v > 60:
            raise ValueError("Years of experience must be at most 60")
        return v

    @field_validator("bio")
    @classmethod
    def validate_bio(cls, v: str) -> str:
        v = v.strip()
        if len(v) > 500:
            raise ValueError("Bio must be at most 500 characters")
        return v
    
    @field_validator("profile_pic")
    def validate_logo(cls, v: UploadFile):
        if v is None:
            return v
        if v.content_type not in ALLOWED_PROFILE_PIC_TYPES:
            raise ValueError("Logo must be JPG, PNG or WebP")
        if v.size and v.size > MAX_PROFILE_PIC_SIZE:
            raise ValueError("Logo must be smaller than 1MB")
        return v

def create_recruiter_profile_form(
    first_name: str = Form(...),
    last_name: Optional[str] = Form(default=""),
    company: str = Form(...),
    role: str = Form(...),
    years_of_experience: int = Form(default=0),
    bio: str = Form(default=""),
) -> RecruiterProfileSchema:
    try:
        return RecruiterProfileSchema(
            first_name=first_name,
            last_name=last_name,
            company=company,
            role=role,
            years_of_experience=years_of_experience,
            bio=bio,
        )
    except ValidationError as e:
        raise RequestValidationError(e.errors())



VALID_CURRENCIES = {"INR", "USD", "EUR", "GBP"}

class RecruiterSettingsSchema(BaseModel):
    country: Optional[str] = None
    currency_type: str = "INR"

    @field_validator("country")
    @classmethod
    def validate_country(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip().upper()
        if len(v) != 2:
            raise ValueError("Country must be a valid ISO2 code e.g. IN, US")
        return v

    @field_validator("currency_type")
    @classmethod
    def validate_currency_type(cls, v: str) -> str:
        v = v.strip().upper()
        if v not in VALID_CURRENCIES:
            raise ValueError(f"currency_type must be one of {VALID_CURRENCIES}")
        return v

class EmailOtpSchema(BaseModel):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def validate_new_email(cls, v: str) -> str:
        if len(v) > 254:
            raise ValueError("Email must be at most 254 characters")
        return v.lower().strip()

class EmailOtpVerifySchema(BaseModel):
    otp: str
    email: EmailStr

    @field_validator("otp")
    @classmethod
    def validate_otp(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("OTP is required")
        if not v.isdigit():
            raise ValueError("OTP must contain only digits")
        if len(v) != 6:
            raise ValueError("OTP must be exactly 6 digits")
        return v

    @field_validator("email")
    @classmethod
    def validate_new_email(cls, v: str) -> str:
        if len(v) > 254:
            raise ValueError("Email must be at most 254 characters")
        return v.lower().strip()


class PhoneOtpSchema(BaseModel):
    phone: str

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Phone number is required")
        digits = v.replace("+", "").replace("-", "").replace(" ", "")
        if not digits.isdigit():
            raise ValueError("Phone number must contain only digits, +, - or spaces")
        if len(digits) < 7:
            raise ValueError("Phone number must be at least 7 digits")
        if len(digits) > 15:
            raise ValueError("Phone number must be at most 15 digits")
        return v


class PhoneOtpVerifySchema(BaseModel):
    otp: str
    phone: str

    @field_validator("otp")
    @classmethod
    def validate_otp(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("OTP is required")
        if not v.isdigit():
            raise ValueError("OTP must contain only digits")
        if len(v) != 6:
            raise ValueError("OTP must be exactly 6 digits")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Phone number is required")
        digits = v.replace("+", "").replace("-", "").replace(" ", "")
        if not digits.isdigit():
            raise ValueError("Phone number must contain only digits, +, - or spaces")
        if len(digits) < 7:
            raise ValueError("Phone number must be at least 7 digits")
        if len(digits) > 15:
            raise ValueError("Phone number must be at most 15 digits")
        return v