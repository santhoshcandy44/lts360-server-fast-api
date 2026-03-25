from datetime import date, datetime
from decimal import Decimal
import json

from fastapi import File, Form, Query, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, EmailStr, Field, ValidationError, field_validator, model_validator
from typing import Annotated, Dict, Optional, List

VALID_APPLICANT_STEPS = [
    "PROFESSIONAL_INFO", "EDUCATION", "EXPERIENCE",
    "SKILLS", "LANGUAGES", "RESUME", "CERTIFICATES"
]

VALID_LANGUAGES = {
    "en": "English", "es": "Spanish", "zh": "Mandarin Chinese", "hi": "Hindi",
    "ar": "Arabic", "bn": "Bengali", "pt": "Portuguese", "ru": "Russian",
    "ja": "Japanese", "pa": "Punjabi", "de": "German", "jv": "Javanese",
    "ko": "Korean", "fr": "French", "tr": "Turkish", "vi": "Vietnamese",
    "it": "Italian", "mr": "Marathi", "ur": "Urdu", "te": "Telugu",
    "ta": "Tamil", "gu": "Gujarati", "pl": "Polish", "uk": "Ukrainian",
    "ml": "Malayalam", "kn": "Kannada", "or": "Oriya (Odia)", "th": "Thai",
    "nl": "Dutch", "el": "Greek", "sv": "Swedish", "ro": "Romanian",
    "hu": "Hungarian", "cs": "Czech", "he": "Hebrew", "fa": "Persian (Farsi)",
    "ms": "Malay", "my": "Burmese", "am": "Amharic", "sr": "Serbian",
    "fi": "Finnish", "no": "Norwegian", "sk": "Slovak", "hr": "Croatian",
    "zu": "Zulu", "xh": "Xhosa", "af": "Afrikaans", "sw": "Swahili",
    "ne": "Nepali", "si": "Sinhala"
}

VALID_PROFICIENCIES = {
    "fluent": "Fluent",
    "basic": "Basic",
    "intermediate": "Intermediate"
}

VALID_EMPLOYMENT_TYPES = ["full_time", "part_time", "contract", "intern", "freelance"]

ALLOWED_IMAGE_TYPES = {"image/jpg", "image/jpeg", "image/png"}

MAX_IMAGE_SIZE = 1 * 1024 * 1024

class GuestGetJobsSchema(BaseModel):
    s: Optional[str] = None
    s_latitude: Optional[float] = None
    s_longitude: Optional[float] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    industries:     Optional[List[str]]  = None 
    page_size: Optional[int] = None
    next_token: Optional[str] = None
    previous_token: Optional[str] = None
    work_modes: Optional[str] = None        
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None

    @field_validator("s")
    def validate_s(cls, v):
        if v and len(v) > 100:
            raise ValueError("Query string must be between 0 and 100 characters")
        return v

    @field_validator("s_latitude")
    def validate_s_latitude(cls, v):
        if v is not None and not (-90 <= v <= 90):
            raise ValueError("S Latitude must be between -90 and 90")
        return v

    @field_validator("s_longitude")
    def validate_s_longitude(cls, v):
        if v is not None and not (-180 <= v <= 180):
            raise ValueError("S Longitude must be between -180 and 180")
        return v

    @field_validator("latitude")
    def validate_latitude(cls, v):
        if v is not None and not (-90 <= v <= 90):
            raise ValueError("Latitude must be between -90 and 90")
        return v

    @field_validator("longitude")
    def validate_longitude(cls, v):
        if v is not None and not (-180 <= v <= 180):
            raise ValueError("Longitude must be between -180 and 180")
        return v
    
    @field_validator("salary_min", "salary_max")
    def validate_salary(cls, v):
        if v is not None and v < -1:
            raise ValueError("Salary must be a number or -1")
        return v
 
    @field_validator("industries")
    def validate_industries(cls, v):
        if v is not None:
            if not all(isinstance(i, str) and i.strip() for i in v):
                raise ValueError("Each industry must be a non-empty string")
        return v
        
    @field_validator("page_size")
    def validate_page_size(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Invalid page size format")
        return v

def create_guest_get_jobs_params(
    s: Optional[str] = Query(default=None),

    s_latitude: Optional[float] = Query(default=None),
    s_longitude: Optional[float] = Query(default=None),

    latitude: Optional[float] = Query(default=None),
    longitude: Optional[float] = Query(default=None),

    industries: Optional[List[str]] = Query(default=None),

    page_size: Optional[int] = Query(default=20),
    next_token: Optional[str] = Query(default=None),
    previous_token: Optional[str] = Query(default=None),

    work_modes: Optional[List[str]] = Query(default=None),

    salary_min: Optional[int] = Query(default=None),
    salary_max: Optional[int] = Query(default=None),
):
    try:
        return GuestGetJobsSchema(
            s=s,

            s_latitude=s_latitude,
            s_longitude=s_longitude,

            latitude=latitude,
            longitude=longitude,

            industries=industries,

            page_size=page_size,
            next_token=next_token,
            previous_token=previous_token,

            work_modes=work_modes,

            salary_min=salary_min,
            salary_max=salary_max,
        )
    except ValidationError as e:
        raise RequestValidationError(e.errors())

class GetJobsSchema(BaseModel):
    s: Optional[str] = None
    s_latitude: Optional[float] = None
    s_longitude: Optional[float] = None
    industries:     Optional[List[int]]  = None 
    page_size: Optional[int] = None
    next_token: Optional[str] = None
    previous_token: Optional[str] = None
    work_modes: Optional[str] = None        
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None

    @field_validator("s")
    def validate_s(cls, v):
        if v and len(v) > 100:
            raise ValueError("Query string must be between 0 and 100 characters")
        return v

    @field_validator("s_latitude")
    def validate_s_latitude(cls, v):
        if v is not None and not (-90 <= v <= 90):
            raise ValueError("S Latitude must be between -90 and 90")
        return v

    @field_validator("s_longitude")
    def validate_s_longitude(cls, v):
        if v is not None and not (-180 <= v <= 180):
            raise ValueError("S Longitude must be between -180 and 180")
        return v
    
    @field_validator("salary_min", "salary_max")
    def validate_salary(cls, v):
        if v is not None and v < -1:
            raise ValueError("Salary must be a number or -1")
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

def create_get_jobs_params(
    s: Optional[str] = Query(default=None),

    s_latitude: Optional[float] = Query(default=None),
    s_longitude: Optional[float] = Query(default=None),
    
    industries: Optional[List[int]] = Query(default=None),

    page_size: Optional[int] = Query(default=20),
    next_token: Optional[str] = Query(default=None),
    previous_token: Optional[str] = Query(default=None),

    work_modes: Optional[List[str]] = Query(default=None),

    salary_min: Optional[int] = Query(default=None),
    salary_max: Optional[int] = Query(default=None),
):
    try:
        return GetJobsSchema(
            s=s,

            s_latitude=s_latitude,
            s_longitude=s_longitude,

            industries=industries,

            page_size=page_size,
            next_token=next_token,
            previous_token=previous_token,

            work_modes=work_modes,

            salary_min=salary_min,
            salary_max=salary_max,
        )
    except ValidationError as e:
        raise RequestValidationError(e.errors())
    
class JobIdSchema(BaseModel):
    job_id: int

    @field_validator("job_id")
    def validate_local_job_id(cls, v):
        if v <= 0:
            raise ValueError("Invalid job id")
        return v    
    
class GetSavedJobsSchema(BaseModel):
    page_size:  Optional[int]   = None
    next_token: Optional[str]   = None

    @field_validator("page_size")
    def validate_page_size(cls, v):
        if v is not None and v <= 0:
            raise ValueError("Page size must be a positive integer")
        return v
    
#Applicant Profile
class ApplicantProfileSchema(BaseModel):
    supported_steps: List[str]
    @field_validator("supported_steps")
    def validate_steps(cls, v):
        steps = v if isinstance(v, list) else [v]
        invalid = [s for s in steps if s not in VALID_APPLICANT_STEPS]
        if invalid:
            raise ValueError(f"Invalid steps: {', '.join(invalid)}")
        return steps

def application_profile_schema_params(supported_steps: List[str] = Query(...)):
    try:
        return ApplicantProfileSchema(supported_steps=supported_steps)
    except ValidationError as e:
        raise RequestValidationError(e.errors())       

class UpdateProfessionalInfoSchema(BaseModel):
    supported_steps: List[str]
    first_name:      str
    last_name:       str
    email:           EmailStr
    gender:          str
    intro:           str
    profile_pic:     Optional[UploadFile] = None

    @field_validator("supported_steps")
    @classmethod
    def validate_steps(cls, v):
        steps = list(v) if not isinstance(v, list) else v
        invalid = [s for s in steps if s not in VALID_APPLICANT_STEPS]
        if invalid:
            raise ValueError(f"Invalid steps: {', '.join(invalid)}")
        return steps

    @field_validator("first_name")
    @classmethod
    def validate_first_name(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("First name is required")
        if len(v) < 2:
            raise ValueError("First name must be at least 2 characters")
        if len(v) > 70:
            raise ValueError("First name must be under 70 characters")
        return v

    @field_validator("last_name")
    @classmethod
    def validate_last_name(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Last name is required")
        if len(v) < 2:
            raise ValueError("Last name must be at least 2 characters")
        if len(v) > 70:
            raise ValueError("Last name must be under 70 characters")
        return v

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, v):
        if v not in ["Male", "Female", "Other"]:
            raise ValueError("Gender must be Male, Female, or Other")
        return v

    @field_validator("intro")
    @classmethod
    def validate_intro(cls, v):
        v = v.strip()
        if len(v) < 10:
            raise ValueError("Intro must be at least 10 characters")
        if len(v) > 300:
            raise ValueError("Intro must be under 300 characters")
        return v

    @field_validator("profile_pic")
    @classmethod
    def validate_profile_pic(cls, v):
        if v is None:
            return v
        if v.content_type not in ALLOWED_IMAGE_TYPES:
            raise ValueError(f"Invalid file type. Only jpg, jpeg, png allowed")
        if not v.filename or not v.filename.strip():
            raise ValueError("File name is required")
        if v.size and v.size > MAX_IMAGE_SIZE:
            raise ValueError(f"Image must be under 1MB")
        return v
    
def create_update_professional_info_form(
    supported_steps: List[str] = Form(...),
    first_name:      str       = Form(...),
    last_name:       str       = Form(...),
    email:           str       = Form(...),
    gender:          str       = Form(...),
    intro:           str       = Form(...),
    profile_pic:     Optional[UploadFile] = File(default=None),
):
    try:
        return UpdateProfessionalInfoSchema(
            supported_steps=list(supported_steps),
            first_name=first_name,
            last_name=last_name,
            email=email,
            gender=gender,
            intro=intro,
            profile_pic=profile_pic,
        )
    except ValidationError as e:
        raise RequestValidationError(e.errors())   
    
class Education(BaseModel):
    organization_name:     str
    field_of_study:        str
    start_date:            date
    is_currently_studying: bool
    end_date:              Optional[date]  = None
    grade: Optional[
    Annotated[Decimal, Field(max_digits=5, decimal_places=1)]] = None
    
    @field_validator("organization_name")
    @classmethod
    def validate_institution(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Organization name is required")
        if len(v) > 255:
            raise ValueError("Organization name must be under 255 characters")
        return v

    @field_validator("field_of_study")
    @classmethod
    def validate_field_of_study(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Field of study is required")
        if len(v) > 255:
            raise ValueError("Field of study must be under 255 characters")
        return v

    @field_validator("start_date", mode="before")
    @classmethod
    def validate_start_date(cls, v) -> date:
        if not v:
            raise ValueError("Start date is required")
        try:
            return datetime.strptime(str(v), "%d-%m-%Y").date()
        except ValueError:
            raise ValueError("Start date must be in format dd-MM-yyyy e.g. 25-12-2024")

    @field_validator("end_date", mode="before")
    @classmethod
    def validate_end_date(cls, v) -> Optional[date]:
        if not v or v == "":
            return None
        try:
            return datetime.strptime(str(v), "%d-%m-%Y").date()
        except ValueError:
            raise ValueError("End date must be in format dd-MM-yyyy e.g. 25-12-2024")
        
    @field_validator("grade")
    @classmethod
    def validate_grade(cls, v):
        if v is not None and not (0.0 <= v):
            raise ValueError("Grade must be greater than 0")
        return v

    @model_validator(mode="after")
    def validate_education(self):
        if self.is_currently_studying:
            if self.end_date is not None:
                raise ValueError("If currently studying, end_date must be null")
            if self.grade is not None:
                raise ValueError("If currently studying, grade must be null")
        else:
            if self.end_date is None:
                raise ValueError("End date is required if not currently studying")
            if self.end_date <= self.start_date:
                raise ValueError("End date must be after start date")
            if self.end_date > date.today():
                raise ValueError("End date cannot be in the future")
            if self.grade is None:
                raise ValueError("Grade is required if not currently studying")
        return self

class UpdateEducationSchema(BaseModel):
    supported_steps: List[str]
    educations: List[Education]

    @field_validator("supported_steps")
    def validate_steps(cls, v):
        steps = v if isinstance(v, list) else [v]
        invalid = [s for s in steps if s not in VALID_APPLICANT_STEPS]
        if invalid:
            raise ValueError(f"Invalid steps: {', '.join(invalid)}")
        return steps

    @field_validator("educations")
    def validate_educations(cls, v):
        if not (1 <= len(v) <= 3):
            raise ValueError("At least one education is required (max 3)")
        return v

class Experience(BaseModel):
    is_experienced:     bool
    job_title:         str
    employment_type:   str
    organization_name: str
    is_currently_working:    bool
    start_date:        date
    end_date:          Optional[date] = None
    location:          str

    @field_validator("is_experienced")
    @classmethod
    def validate_experienced(cls, v):
        if v is not True:
            raise ValueError("experienced must be true")
        return v

    @field_validator("job_title")
    @classmethod
    def validate_job_title(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Job title is required")
        if len(v) > 255:
            raise ValueError("Job title must be under 255 characters")
        return v

    @field_validator("employment_type")
    @classmethod
    def validate_employment_type(cls, v):
        if v not in VALID_EMPLOYMENT_TYPES:
            raise ValueError(f"Employment type must be one of: {', '.join(VALID_EMPLOYMENT_TYPES)}")
        return v

    @field_validator("organization_name")
    @classmethod
    def validate_organization_name(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Company name is required")
        if len(v) > 255:
            raise ValueError("Company name must be under 255 characters")
        return v

    @field_validator("location")
    @classmethod
    def validate_location(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Location is required")
        if len(v) > 255:
            raise ValueError("Location must be under 255 characters")
        return v

    @field_validator("start_date", mode="before")
    @classmethod
    def validate_start_date(cls, v) -> date:
        if not v:
            raise ValueError("Start date is required")
        try:
            return datetime.strptime(str(v), "%d-%m-%Y").date()
        except ValueError:
            raise ValueError("Start date must be in format dd-MM-yyyy e.g. 25-12-2024")

    @field_validator("end_date", mode="before")
    @classmethod
    def validate_end_date(cls, v) -> Optional[date]:
        if not v or v == "":
            return None
        try:
            return datetime.strptime(str(v), "%d-%m-%Y").date()
        except ValueError:
            raise ValueError("End date must be in format dd-MM-yyyy e.g. 25-12-2024")

    @model_validator(mode="after")
    def validate_experience(self):
        if not self.is_currently_working:
            if self.end_date is None:
                raise ValueError("End date is required if not current job")
            if self.end_date <= self.start_date:
                raise ValueError("End date must be after start date")
            if self.end_date > date.today():
                raise ValueError("End date cannot be in the future")
        if self.start_date > date.today():
            raise ValueError("Start date cannot be in the future")
        return self
    
class UpdateExperienceSchema(BaseModel):
    supported_steps: List[str]
    experiences:     List[Experience]

    @field_validator("supported_steps")
    @classmethod
    def validate_steps(cls, v):
        steps = list(v) if not isinstance(v, list) else v
        invalid = [s for s in steps if s not in VALID_APPLICANT_STEPS]
        if invalid:
            raise ValueError(f"Invalid steps: {', '.join(invalid)}")
        return steps

    @field_validator("experiences")
    @classmethod
    def validate_experiences(cls, v):
        if not v:
            raise ValueError("At least one experience is required")
        if len(v) > 5:
            raise ValueError("Maximum 5 experiences allowed")
        return v
    
class UpdateNoExperienceSchema(BaseModel):
    supported_steps: List[str]

    @field_validator("supported_steps")
    def validate_steps(cls, v):
        steps = v if isinstance(v, list) else [v]
        invalid = [s for s in steps if s not in VALID_APPLICANT_STEPS]
        if invalid:
            raise ValueError(f"Invalid steps: {', '.join(invalid)}")
        return steps

class Skill(BaseModel):
    name: str
    code: str

    @field_validator("name")
    @classmethod
    def validate_name(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Skill name is required")
        if len(v) > 100:
            raise ValueError("Skill name must be under 100 characters")
        return v

    @field_validator("code")
    @classmethod
    def validate_code(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Skill code is required")
        return v

class UpdateSkillsSchema(BaseModel):
    supported_steps: List[str]
    skills:          List[Skill]

    @field_validator("supported_steps")
    @classmethod
    def validate_steps(cls, v):
        steps = list(v) if not isinstance(v, list) else v
        invalid = [s for s in steps if s not in VALID_APPLICANT_STEPS]
        if invalid:
            raise ValueError(f"Invalid steps: {', '.join(invalid)}")
        return steps

    @field_validator("skills")
    @classmethod
    def validate_skills(cls, v):
        if not v:
            raise ValueError("At least one skill is required")
        if len(v) > 20:
            raise ValueError("Maximum 20 skills allowed")
        return v

class LanguageCode(BaseModel):
    code: str
    name: str

class ProficiencyValue(BaseModel):
    value: str
    name: str

class Language(BaseModel):
    language: LanguageCode
    proficiency: ProficiencyValue

    @model_validator(mode="after")
    def validate_language_proficiency(self):
        lang = self.language
        prof = self.proficiency
        if VALID_LANGUAGES.get(lang.code) != lang.name:
            raise ValueError(f"Invalid language code-name combination: {lang.code}/{lang.name}")
        if VALID_PROFICIENCIES.get(prof.value) != prof.name:
            raise ValueError(f"Invalid proficiency value-name combination: {prof.value}/{prof.name}")
        return self

class UpdateLanguagesSchema(BaseModel):
    supported_steps: List[str]
    languages: List[Language]

    @field_validator("supported_steps")
    def validate_steps(cls, v):
        steps = v if isinstance(v, list) else [v]
        invalid = [s for s in steps if s not in VALID_APPLICANT_STEPS]
        if invalid:
            raise ValueError(f"Invalid steps: {', '.join(invalid)}")
        return steps

    @field_validator("languages")
    def validate_languages(cls, v):
        if not v:
            raise ValueError("Languages cannot be empty")
        if len(v) > 5:
            raise ValueError("Languages can't exceed 5")
        return v

ALLOWED_RESUME_TYPES = [
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
]

MAX_RESUME_SIZE = 5 * 1024 * 1024  

class UpdateResumeSchema(BaseModel):
    supported_steps: List[str]
    resume:          UploadFile

    model_config = {"arbitrary_types_allowed": True}

    @field_validator("supported_steps")
    @classmethod
    def validate_steps(cls, v):
        steps = list(v) if not isinstance(v, list) else v
        invalid = [s for s in steps if s not in VALID_APPLICANT_STEPS]
        if invalid:
            raise ValueError(f"Invalid steps: {', '.join(invalid)}")
        return steps

    @field_validator("resume")
    @classmethod
    def validate_resume(cls, v: UploadFile):
        if v is None:
            raise ValueError("Resume is required")
        if not v.filename or not v.filename.strip():
            raise ValueError("Resume file name is required")
        if v.content_type not in ALLOWED_RESUME_TYPES:
            raise ValueError("Invalid file type. Allowed: pdf, doc, docx")
        if v.size and v.size > MAX_RESUME_SIZE:
            raise ValueError("Resume must be under 5MB")
        return v

def create_update_resume_form(
    supported_steps: List[str] = Form(...),
    resume:          UploadFile = File(...),
):
    try:
        return UpdateResumeSchema(
            supported_steps=list(supported_steps),
            resume=resume,
        )
    except ValidationError as e:
        raise RequestValidationError(e.errors())

ALLOWED_CERT_TYPES = ["image/jpeg", "image/jpg", "image/png"]
MAX_CERT_SIZE = 1 * 1024 * 1024 

class Certificate(BaseModel):
    certificate_id:  Optional[int] = None      
    issued_by: str
    key:str

    @field_validator("issued_by")
    @classmethod
    def validate_issued_by(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Issued by is required")
        if len(v) > 50:
            raise ValueError("Issued by must be under 50 characters")
        return v
    
    @field_validator("key")
    @classmethod
    def validate_key(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Key is required")
        return v

class UpdateCertificatesSchema(BaseModel):
    supported_steps:   List[str]
    certificates_info: List[Certificate]
    images:            Dict[str, UploadFile]

    @field_validator("supported_steps")
    def validate_steps(cls, v):
        steps = list(v) if not isinstance(v, list) else v
        invalid = [s for s in steps if s not in VALID_APPLICANT_STEPS]
        if invalid:
            raise ValueError(f"Invalid steps: {', '.join(invalid)}")
        return steps

    @field_validator("certificates_info")
    def validate_certificates(cls, v):
        active = [c for c in v if c.certificate_id != 0]
        if not active:
            raise ValueError("At least one certificate is required")
        if len(active) > 5:
            raise ValueError("Maximum 5 certificates allowed")
        return v
    @field_validator("images")
    def validate_images(cls, v):
        for key, f in v.items():
            if f.content_type not in ALLOWED_CERT_TYPES:
                raise ValueError(f"{key}: Invalid image type ({f.filename})")

            if f.size and f.size > MAX_CERT_SIZE:
                raise ValueError(f"{key}: {f.filename} must be under 1MB")

        return v

    @model_validator(mode="after")
    def validate_certificates_info_and_images(self):
        for cert in self.certificates_info:
            if cert.certificate_id is None:
                if f"certificate_{cert.key}" not in self.images:
                    raise ValueError(f"Image is required for new certificate: {cert.key}")

            else:
                if cert.key in self.images:
                    continue
        return self

async def create_update_certificates_form(
    request:Request,
    supported_steps:   List[str]        = Form(...),
    certificates_info: str              = Form(...)
):
    try:
        parsed_certificates = json.loads(certificates_info)
        form = await request.form()

        images_dict = {}

        for key, value in form.items():
            if hasattr(value, "filename"):
                images_dict[key] = value
        return UpdateCertificatesSchema(
            supported_steps=   supported_steps,
            certificates_info= parsed_certificates,
            images=            images_dict,
        )
    except ValidationError as e:
        raise RequestValidationError(e.errors())

class SkillSearchSuggestionsSchema(BaseModel):
    query: str

    @field_validator("query")
    def validate_query(cls, v):
        v = v.strip()
        if not v:
            raise ValueError("Query cannot be empty")
        return v
    
class LocationSearchSuggestionsSchema(BaseModel):
    query: str

    @field_validator("query")
    def validate_query(cls, v):
        if not v or not v.strip():
            raise ValueError("Query cannot be empty")
        return v

class RoleSearchSuggestionsSchema(BaseModel):
    query: str

    @field_validator("query")
    def validate_query(cls, v):
        if not v or not v.strip():
            raise ValueError("Query cannot be empty")
        return v    

class Industry(BaseModel):
    code: str
    is_selected: bool
    name: Optional[str] = None
    description: Optional[str] = None
   
class UpdateIndustriesSchema(BaseModel):
    industries: List[Industry]

    @field_validator("industries")
    def validate_industries(cls, v):
        if not any(i.is_selected for i in v):
            raise ValueError("At least one industry must be selected")
        return v
      