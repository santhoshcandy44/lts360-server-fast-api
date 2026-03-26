"""
models.py
─────────
Django models → SQLModel (SQLAlchemy) conversion.
Matches the existing pattern from your services models.
"""

from datetime import date, datetime, timezone, timedelta
from decimal import Decimal
import random
from typing import List, Optional

from sqlmodel import Field, Relationship, SQLModel

from sqlalchemy import (
    BigInteger, Column, Date, DateTime,
    Enum as SAEnum, ForeignKey, Integer,
    JSON, Numeric, String, Text, UniqueConstraint, event , Index
)

from sqlalchemy.dialects.mysql import MEDIUMINT
from sqlalchemy.orm import Session

class Plan(SQLModel, table=True):
    __tablename__ = "lts360_jobs_console_plans"

    id:       Optional[int] = Field(default=None, primary_key=True)
    name:     str           = Field(max_length=100)
    is_free:  bool          = Field(default=False)
    price:    Decimal       = Field(sa_column=Column(Numeric(10, 2), nullable=False, default=0))
    features: dict          = Field(sa_column=Column(JSON, nullable=False))
    created_at:        datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:        datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))

    recruiters: List["RecruiterProfile"] = Relationship(
        back_populates="plan",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

RECRUITER_ROLE_DISPLAY = {
    "RECRUITER":          "Recruiter",
    "HIRING_MANAGER":     "Hiring Manager",
    "TALENT_ACQUISITION": "Talent Acquisition",
    "HR":                 "HR",
}

class RecruiterProfile(SQLModel, table=True):
    __tablename__ = "recruiter_profiles"

    id:                 Optional[int] = Field(default=None, primary_key=True)
    external_user_id:   str           = Field(max_length=255)
    first_name:         str           = Field(max_length=100)
    last_name:          Optional[str] = Field(default=None, max_length=100, nullable=True)
    email:              str           = Field(max_length=254)
    role:               str           = Field(
                                            sa_column=Column(
                                                SAEnum("RECRUITER", "HIRING_MANAGER", "TALENT_ACQUISITION", "HR",
                                                       name="recruiter_role"),
                                                nullable=False, default="RECRUITER",
                                            )
                                        )
    organization_name:            str           = Field(max_length=50)
    phone:              Optional[str] = Field(default=None, max_length=20, nullable=True)
    profile_pic_url:    Optional[str] = Field(default=None, nullable=True)
    profile_pic_url_small:    Optional[str] = Field(default=None, nullable=True)
    bio:                str           = Field(sa_column=Column(Text, nullable=False))
    years_of_experience: int          = Field(default=1)
    created_at:         datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:         datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_verified:        bool          = Field(default=False)

    plan_id:            int           = Field(sa_column=Column(Integer, ForeignKey("lts360_jobs_console_plans.id", ondelete="RESTRICT"), nullable=False, default=1))
    subscription_date:  datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    trial_end_date:     datetime      = Field(default_factory=lambda: datetime.now(timezone.utc) + timedelta(days=15))
    is_trial_active:    bool          = Field(default=True)

    last_sign_in:       datetime       = Field(nullable=False)
    
    created_at:        datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:        datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))

    plan: Optional[Plan] = Relationship(
        back_populates="recruiters",
        sa_relationship_kwargs={"lazy": "selectin"},
    )
    organizations: List["Organization"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"lazy": "selectin"},
    )
    jobs: List["Job"] = Relationship(
        back_populates="posted_by",
        sa_relationship_kwargs={"lazy": "selectin"},
    )
    settings: Optional["RecruiterSettings"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    @property
    def role_display(self) -> str:
        return RECRUITER_ROLE_DISPLAY.get(self.role, self.role.replace("_", " ").title())

class RecruiterSettings(SQLModel, table=True):
    __tablename__ = "recruiter_settings"

    id:            Optional[int] = Field(default=None, primary_key=True)
    user_id:       int           = Field(sa_column=Column(Integer, ForeignKey("recruiter_profiles.id", ondelete="CASCADE"), unique=True, nullable=False))
    country_id:    Optional[int] = Field(default=None, sa_column=Column(MEDIUMINT(unsigned=True), ForeignKey("countries.id", ondelete="SET NULL"), nullable=True, default=101))
    currency_type: str           = Field(
                                       sa_column=Column(
                                           SAEnum("USD", "EUR", "GBP", "INR", name="recruiter_currency"),
                                           nullable=False, default="INR",
                                       )
                                   )
    created_at:        datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:        datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))

    user: Optional[RecruiterProfile] = Relationship(
        back_populates="settings",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    country: Optional["Country"] = Relationship(
        back_populates="settings",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

class Organization(SQLModel, table=True):
    __tablename__ = "organizations"

    id:                   Optional[int] = Field(default=None, primary_key=True)
    organization_id:      int           = Field(sa_column=Column(BigInteger, unique=True, nullable=False))
    user_id:              int           = Field(sa_column=Column(Integer, ForeignKey("recruiter_profiles.id", ondelete="CASCADE"), nullable=False, index=True))
    name:    str           = Field(max_length=255)
    logo:                 Optional[str] = Field(default=None, nullable=True)
    email:                str           = Field(max_length=254)
    address: str           = Field(max_length=255)
    website:              str           = Field(max_length=200)
    country_id:           Optional[int] = Field(default=None, sa_column=Column(MEDIUMINT(unsigned=True), ForeignKey("countries.id", ondelete="SET NULL"), nullable=True))
    state_id:             Optional[int] = Field(default=None, sa_column=Column(MEDIUMINT(unsigned=True), ForeignKey("states.id", ondelete="SET NULL"), nullable=True))
    location_id:          Optional[int] = Field(default=None, sa_column=Column(MEDIUMINT(unsigned=True), ForeignKey("cities.id", ondelete="SET NULL"), nullable=True))
    postal_code:          str           = Field(max_length=10)

    created_at:        datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:        datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    country: Optional["Country"] = Relationship(
        back_populates="organizations",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    state: Optional["State"] = Relationship(
        back_populates="organizations",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    city: Optional["City"] = Relationship(
        back_populates="organizations",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    user: Optional[RecruiterProfile] = Relationship(
        back_populates="organizations",
        sa_relationship_kwargs={"lazy": "selectin"},
    )
   
    jobs: List["Job"] = Relationship(
        back_populates="organization",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

class Education(SQLModel, table=True):
    __tablename__ = "job_educations"

    id:          Optional[int] = Field(default=None, primary_key=True)
    name:        str           = Field(max_length=100, sa_column=Column(String(100), unique=True, nullable=False))
    code:        str           = Field(max_length=50,  sa_column=Column(String(50),  unique=True, nullable=False))
    description: str           = Field(default="", sa_column=Column(Text, nullable=False, default=""))

    created_at:        datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:        datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))

    jobs: List["Job"] = Relationship(
        back_populates="education",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

class JobIndustry(SQLModel, table=True):
    __tablename__ = "job_industries"

    id:          Optional[int] = Field(default=None, primary_key=True)
    name:        str           = Field(max_length=100, sa_column=Column(String(100), unique=True, nullable=False))
    code:        str           = Field(max_length=50,  sa_column=Column(String(50),  unique=True, nullable=False))
    description: str           = Field(default="", sa_column=Column(Text, nullable=False, default=""))

    created_at:        datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:        datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))

    jobs: List["Job"] = Relationship(
        back_populates="industry",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    user_industries: List["UserJobIndustry"] = Relationship(
        back_populates="industry",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

class Department(SQLModel, table=True):
    __tablename__ = "job_departments"

    id:          Optional[int] = Field(default=None, primary_key=True)
    name:        str           = Field(max_length=100, sa_column=Column(String(100), unique=True, nullable=False))
    code:        str           = Field(max_length=50,  sa_column=Column(String(50),  unique=True, nullable=False))  # was max_length=10 — fixed
    description: str           = Field(default="", sa_column=Column(Text, nullable=False, default=""))

    created_at:        datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:        datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))

    jobs: List["Job"] = Relationship(
        back_populates="department",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

class Role(SQLModel, table=True):
    __tablename__ = "job_roles"

    id:          Optional[int] = Field(default=None, primary_key=True)
    name:        str           = Field(max_length=100)
    code:        str           = Field(max_length=50, sa_column=Column(String(50), unique=True, nullable=False))
    description: str           = Field(default="", sa_column=Column(Text, nullable=False, default=""))
    popularity:  int           = Field(default=0)

    created_at:        datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:        datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))

    jobs: List["Job"] = Relationship(
        back_populates="role",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

class Skill(SQLModel, table=True):
    __tablename__ = "job_skills"

    id:          Optional[int] = Field(default=None, primary_key=True)
    code:        str           = Field(max_length=50, sa_column=Column(String(50), unique=True, nullable=False))
    name:        str           = Field(max_length=100)
    description: str           = Field(default="", sa_column=Column(Text, nullable=False, default=""))
    popularity:  int           = Field(default=0)

    created_at:        datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:        datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))

    must_have_jobs:    List["JobMustHaveSkill"]    = Relationship(back_populates="skill", sa_relationship_kwargs={"lazy": "selectin"})
    good_to_have_jobs: List["JobGoodToHaveSkill"]  = Relationship(back_populates="skill", sa_relationship_kwargs={"lazy": "selectin"})

CURRENCY_SYMBOLS = {
    "INR": "₹",
    "USD": "$",
    "EUR": "€",
    "GBP": "£",
}

EMPLOYMENT_TYPE_DISPLAY = {
    "full_time":  "Full Time",
    "part_time":  "Part Time",
    "contract":   "Contract",
    "internship": "Internship",
}

HIGHLIGHTS_MAP = {
    "free_food": {"type": "free_food", "label": "Free Food",  "emoji": "🍕", "description": "Daily meals provided"},
    "free_room": {"type": "free_room", "label": "Free Room",  "emoji": "🏠", "description": "Company housing"},
    "transport": {"type": "transport", "label": "Transport",  "emoji": "🚌", "description": "Commute coverage"},
    "bonus":     {"type": "bonus",     "label": "Bonus",      "emoji": "💰", "description": "Yearly rewards"},
    "health":    {"type": "health",    "label": "Health",     "emoji": "🏥", "description": "Full medical plan"},
    "training":  {"type": "training",  "label": "Training",   "emoji": "🎓", "description": "Skill development"},
    "flexible":  {"type": "flexible",  "label": "Flexible",   "emoji": "⏰", "description": "Choose your schedule"},
}

WORK_MODE_DISPLAY = {
    "remote":   "Remote",
    "office":   "On-site",
    "hybrid":   "Hybrid",
    "flexible": "Flexible",
}

class Job(SQLModel, table=True):
    __tablename__ = "jobs"
    __table_args__ = (
        Index(
            "ft_job_title_description_description",  
            "title",
            "description",
            mysql_prefix="FULLTEXT",            
        ),
    )

    id:                    Optional[int] = Field(default=None, primary_key=True)
    job_id:                int           = Field(sa_column=Column(BigInteger, unique=True, nullable=False))
    title:                 str           = Field(max_length=100)
    work_mode:             str           = Field(
                                               sa_column=Column(
                                                   SAEnum("remote", "office", "hybrid", "flexible", name="job_work_mode"),
                                                   nullable=False, default="office",
                                               )
                                           )
    location_id:           Optional[int] = Field(default=None, sa_column=Column(MEDIUMINT(unsigned=True), ForeignKey("cities.id", ondelete="SET NULL"), nullable=True))
    description:           str           = Field(sa_column=Column(Text, nullable=False))
    experience_type:       str           = Field(
                                               sa_column=Column(
                                                   SAEnum("fresher", "min_max", "fixed", name="job_experience_type"),
                                                   nullable=False, default="fresher",
                                               )
                                           )
    experience_range_min:  int           = Field(default=0)
    experience_range_max:  int           = Field(default=0)
    experience_fixed:      int           = Field(default=0)
    is_salary_not_disclosed:  bool          = Field(default=False)
    salary_min:            Decimal       = Field(sa_column=Column(Numeric(10, 2), nullable=False))
    salary_max:            Decimal       = Field(sa_column=Column(Numeric(10, 2), nullable=False))
    employment_type:       str           = Field(
                                               sa_column=Column(
                                                   SAEnum("full_time", "part_time", "contract", "internship", name="job_employment_type"),
                                                   nullable=False, default="full_time",
                                               )
                                           )
    # FKs to_field="code" → FK to code column
    education_code:        Optional[str] = Field(default=None, sa_column=Column(String(50), ForeignKey("job_educations.code", ondelete="SET NULL"), nullable=True))
    industry_code:         str           = Field(sa_column=Column(String(50), ForeignKey("job_industries.code", ondelete="CASCADE"), nullable=False))
    department_code:       Optional[str] = Field(default=None, sa_column=Column(String(50), ForeignKey("job_departments.code", ondelete="SET NULL"), nullable=True))
    role_code:             Optional[str] = Field(default=None, sa_column=Column(String(50), ForeignKey("job_roles.code", ondelete="SET NULL"), nullable=True))

    vacancies:             int           = Field(default=1)
    highlights:            list          = Field(sa_column=Column(JSON, nullable=False, default=list))
    expiry_date:           datetime      = Field(sa_column=Column(DateTime, nullable=False))
    posted_at:             datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))

    posted_by_id:          int           = Field(sa_column=Column(Integer, ForeignKey("recruiter_profiles.id", ondelete="CASCADE"), nullable=False, index=True))
    organization_id:       int           = Field(sa_column=Column(BigInteger, ForeignKey("organizations.organization_id", ondelete="CASCADE"), nullable=False, index=True))

    status:                str           = Field(
                                               sa_column=Column(
                                                   SAEnum("draft", "published", name="job_status"),
                                                   nullable=False, default="published",
                                               )
                                           )
    approval_status:       str           = Field(
                                               sa_column=Column(
                                                   SAEnum("active", "rejected", name="job_approval_status"),
                                                   nullable=False, default="active",
                                               )
                                           )
    slug:                  str           = Field(max_length=300, sa_column=Column(String(300), unique=True, nullable=False))

    created_at:        datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:        datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    city:    Optional["City"] = Relationship(back_populates="jobs",         sa_relationship_kwargs={"lazy": "selectin"})

    posted_by:    Optional[RecruiterProfile] = Relationship(back_populates="jobs",         sa_relationship_kwargs={"lazy": "selectin"})
    organization: Optional[Organization]     = Relationship(back_populates="jobs",         sa_relationship_kwargs={"lazy": "selectin"})
    education:    Optional[Education]        = Relationship(back_populates="jobs",         sa_relationship_kwargs={"lazy": "selectin", "foreign_keys": "[Job.education_code]"})
    industry:     Optional[JobIndustry]         = Relationship(back_populates="jobs",         sa_relationship_kwargs={"lazy": "selectin", "foreign_keys": "[Job.industry_code]"})
    department:   Optional[Department]       = Relationship(back_populates="jobs",         sa_relationship_kwargs={"lazy": "selectin", "foreign_keys": "[Job.department_code]"})
    role:         Optional[Role]             = Relationship(back_populates="jobs",         sa_relationship_kwargs={"lazy": "selectin", "foreign_keys": "[Job.role_code]"})
    must_have_skills:    List["JobMustHaveSkill"]   = Relationship(back_populates="job",   sa_relationship_kwargs={"lazy": "selectin"})
    good_to_have_skills: List["JobGoodToHaveSkill"] = Relationship(back_populates="job",   sa_relationship_kwargs={"lazy": "selectin"})
    applications:        List["Application"]        = Relationship(back_populates="job",   sa_relationship_kwargs={"lazy": "selectin"})
    bookmarks:           List["UserBookmarkJob"]     = Relationship(back_populates="job",  sa_relationship_kwargs={"lazy": "selectin"})
   
    @property
    def experience_display(self) -> str:
            if self.experience_type == "fresher":
                return "Fresher"

            if self.experience_type == "fixed":
                return f"{self.experience_range_min} years"

            if self.experience_type == "min_max":
                return f"{self.experience_range_min} - {self.experience_range_max} years"

            return ""
    
    @property
    def must_have_skills_display(self) -> List[str]:
        return [
            item.skill.name
            for item in self.must_have_skills
            if item.skill and item.skill.name
        ]
    
    @property
    def good_to_have_skills_display(self) -> List[str]:
        return [
            item.skill.name
            for item in self.must_have_skills
            if item.skill and item.skill.name
        ]

    @property
    def salary_currency_type_display(self) -> str:
        return self.posted_by.settings.currency_type
    
    @property
    def salary_display(self) -> str:
        currency = self.salary_currency_type_display or "INR"
        symbol = CURRENCY_SYMBOLS.get(currency, currency)

        min_val = int(self.salary_min or 0)
        max_val = int(self.salary_max or 0)

        if self.is_salary_not_disclosed:
            return "Not disclosed"

        if min_val == max_val:
            return f"{symbol}{min_val:,}"

        return f"{symbol}{min_val:,} - {symbol}{max_val:,}"

    @property
    def work_mode_display(self) -> str:
        return WORK_MODE_DISPLAY.get(self.employment_type, self.employment_type.replace("_", " ").title()) 
    
    @property
    def employment_type_display(self) -> str:
        return EMPLOYMENT_TYPE_DISPLAY.get(self.employment_type, self.employment_type.replace("_", " ").title())    
    
    @property
    def highlights_display(self) -> list:
        if not self.highlights:
            return []
        return [
            {
                "label":       HIGHLIGHTS_MAP[h]["label"],
                "emoji":       HIGHLIGHTS_MAP[h]["emoji"],
                "description": HIGHLIGHTS_MAP[h]["description"],
            }
            for h in self.highlights
            if h in HIGHLIGHTS_MAP
        ]
    
    @property
    def days_remaining(self) -> int:
        if not self.expiry_date:
            return -1
        now = datetime.now(timezone.utc)
        expiry = self.expiry_date.replace(tzinfo=timezone.utc) if self.expiry_date.tzinfo is None else self.expiry_date
        delta = expiry - now
        return delta.days 

    @property
    def is_expired(self) -> bool:
        if not self.expiry_date:
            return False
        now = datetime.now(timezone.utc)
        expiry = self.expiry_date.replace(tzinfo=timezone.utc) if self.expiry_date.tzinfo is None else self.expiry_date
        return now > expiry
    
    @property
    def is_published(self) -> bool:
        return self.status == "published"

    @property
    def is_draft(self) -> bool:
        return self.status == "draft"

class JobMustHaveSkill(SQLModel, table=True):
    __tablename__ = "job_must_have_skills"
    __table_args__ = (UniqueConstraint("job_id", "code"),)

    id:         Optional[int] = Field(default=None, primary_key=True)
    job_id:     int           = Field(sa_column=Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True))
    code: str           = Field(sa_column=Column(String(50), ForeignKey("job_skills.code", ondelete="CASCADE"), nullable=False))

    job:   Optional[Job]   = Relationship(back_populates="must_have_skills",   sa_relationship_kwargs={"lazy": "selectin"})
    skill: Optional[Skill] = Relationship(back_populates="must_have_jobs",     sa_relationship_kwargs={"lazy": "selectin"})

    created_at:        datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:        datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))

class JobGoodToHaveSkill(SQLModel, table=True):
    __tablename__ = "job_good_have_skills"
    __table_args__ = (UniqueConstraint("job_id", "code"),)

    id:         Optional[int] = Field(default=None, primary_key=True)
    job_id:     int           = Field(sa_column=Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True))
    code: str           = Field(sa_column=Column(String(50), ForeignKey("job_skills.code", ondelete="CASCADE"), nullable=False))

    job:   Optional[Job]   = Relationship(back_populates="good_to_have_skills", sa_relationship_kwargs={"lazy": "selectin"})
    skill: Optional[Skill] = Relationship(back_populates="good_to_have_jobs",   sa_relationship_kwargs={"lazy": "selectin"})

    created_at:        datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:        datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))

#Applicant Profile
class ApplicantProfile(SQLModel, table=True):
    __tablename__ = "applicant_profiles"

    id:                   Optional[int] = Field(default=None, primary_key=True)
    applicant_profile_id: int           = Field(sa_column=Column(BigInteger, unique=True, nullable=False))
    external_user_id:     int           = Field(sa_column=Column(BigInteger, unique=True, nullable=False))
    first_name:           str           = Field(max_length=100)
    last_name:            str           = Field(max_length=100)
    profile_pic_url:      Optional[str] = Field(default=None, sa_column=Column(Text, nullable=True))
    email:                str           = Field(max_length=254)
    intro:                str           = Field(max_length=500)
    gender:               Optional[str] = Field(
                                              sa_column=Column(
                                                  SAEnum("male", "female", "others", name="applicant_gender")
                                              )
                                          )
    phone:                Optional[str] = Field(default=None, max_length=20, nullable=True)
    created_at:           datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:           datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_verified:          bool          = Field(default=False)

    educations:   List["ApplicantProfileEducation"]   = Relationship(back_populates="applicant_profile", sa_relationship_kwargs={"lazy": "selectin"})
    experiences:  List["ApplicantProfileExperience"]  = Relationship(back_populates="applicant_profile", sa_relationship_kwargs={"lazy": "selectin"})
    skills:       List["ApplicantProfileSkill"]       = Relationship(back_populates="applicant_profile", sa_relationship_kwargs={"lazy": "selectin"})
    languages:    List["ApplicantProfileLanguage"]    = Relationship(back_populates="applicant_profile", sa_relationship_kwargs={"lazy": "selectin"})
    resume:       Optional["ApplicantProfileResume"]  = Relationship(back_populates="applicant_profile", sa_relationship_kwargs={"lazy": "selectin"})
    certificates: List["ApplicantProfileCertificate"] = Relationship(back_populates="applicant_profile", sa_relationship_kwargs={"lazy": "selectin"})
    applications: List["Application"]                 = Relationship(back_populates="applicant_profile", sa_relationship_kwargs={"lazy": "selectin"})

    created_at:        datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:        datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_completed(self) -> bool:
        return all([
            self.first_name,
            self.last_name,
            self.gender,
            self.email,
            self.intro,
            self.education_list and len(self.education_list) >= 1,
            self.experience_list and len(self.experience_list) >= 1,
            self.skills_list and len(self.skills_list) >= 1,
            self.languages_list and len(self.languages_list) >= 1,
            self.resume
        ])
    
class ApplicantProfileEducation(SQLModel, table=True):
    __tablename__ = "applicant_profile_educations"

    id:                      Optional[int]     = Field(default=None, primary_key=True)
    applicant_profile_id:    int               = Field(sa_column=Column(BigInteger, ForeignKey("applicant_profiles.applicant_profile_id", ondelete="CASCADE"), nullable=False, index=True))
    organization_name:       str               = Field(max_length=255)
    field_of_study:          str               = Field(max_length=255)
    start_date:              date          = Field(sa_column=Column(Date, nullable=False))
    end_date:                Optional[date]= Field(default=None, sa_column=Column(Date, nullable=True))
    grade:                   Optional[Decimal] = Field(default=None, sa_column=Column(Numeric(5, 1), nullable=True))
    is_currently_studying:      bool              = Field(default=False)

    created_at:        datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:        datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))

    applicant_profile: Optional[ApplicantProfile] = Relationship(back_populates="educations", sa_relationship_kwargs={"lazy": "selectin"})

class ApplicantProfileExperience(SQLModel, table=True):
    __tablename__ = "applicant_profile_experiences"

    id:                   Optional[int] = Field(default=None, primary_key=True)
    applicant_profile_id: int           = Field(sa_column=Column(BigInteger, ForeignKey("applicant_profiles.applicant_profile_id", ondelete="CASCADE"), nullable=False, index=True))
    job_title:            Optional[str] = Field(default=None, max_length=255, nullable=True)
    employment_type:      Optional[str] = Field(
                                              default=None,
                                              sa_column=Column(
                                                  SAEnum("full_time", "part_time", "contract", "intern", "freelance", name="applicant_employment_type"),
                                                  nullable=True,
                                              )
                                          )
    organization_name:         Optional[str] = Field(default=None, max_length=255, nullable=True)
    current_working_here: Optional[bool]= Field(default=False, nullable=True)
    experienced:          bool          = Field(default=True)
    start_date:           Optional[date] = Field(default=None, sa_column=Column(Date, nullable=True))
    end_date:             Optional[date] = Field(default=None, sa_column=Column(Date, nullable=True))
    location:             Optional[str] = Field(default=None, max_length=255, nullable=True)

    created_at:        datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:        datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))

    applicant_profile: Optional[ApplicantProfile] = Relationship(back_populates="experiences", sa_relationship_kwargs={"lazy": "selectin"})

class ApplicantProfileSkill(SQLModel, table=True):
    __tablename__ = "applicant_profile_skills"

    id:                   Optional[int] = Field(default=None, primary_key=True)
    applicant_profile_id: int           = Field(sa_column=Column(BigInteger, ForeignKey("applicant_profiles.applicant_profile_id", ondelete="CASCADE"), nullable=False, index=True))
    name:                str           = Field(max_length=100)
    code:           str           = Field(max_length=50)

    created_at:        datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:        datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))

    applicant_profile: Optional[ApplicantProfile] = Relationship(back_populates="skills", sa_relationship_kwargs={"lazy": "selectin"})

class ApplicantProfileLanguage(SQLModel, table=True):
    __tablename__ = "applicant_profile_languages"

    id:                   Optional[int] = Field(default=None, primary_key=True)
    applicant_profile_id: int           = Field(sa_column=Column(BigInteger, ForeignKey("applicant_profiles.applicant_profile_id", ondelete="CASCADE"), nullable=False, index=True))
    language:             str           = Field(max_length=100)
    language_code:        Optional[str] = Field(default=None, max_length=50, nullable=True)
    proficiency:          Optional[str] = Field(default=None, max_length=50, nullable=True)
    proficiency_value:     Optional[str] = Field(default=None, max_length=50, nullable=True)

    created_at:        datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:        datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))

    applicant_profile: Optional[ApplicantProfile] = Relationship(back_populates="languages", sa_relationship_kwargs={"lazy": "selectin"})

class ApplicantProfileResume(SQLModel, table=True):
    __tablename__ = "applicant_profile_resumes"

    id:                   Optional[int] = Field(default=None, primary_key=True)
    applicant_profile_id: int           = Field(sa_column=Column(BigInteger, ForeignKey("applicant_profiles.applicant_profile_id", ondelete="CASCADE"), unique=True, nullable=False))
    resume_url:  str           = Field(max_length=255)
    name:     str           = Field(max_length=255)
    size:          int           = Field(max_length=50)
    type:          str           = Field(max_length=50)
    last_used:            Optional[datetime] = Field(default=None, sa_column=Column(DateTime, nullable=True))

    created_at:        datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:        datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))

    applicant_profile: Optional[ApplicantProfile] = Relationship(back_populates="resume", sa_relationship_kwargs={"lazy": "selectin"})

class ApplicantProfileCertificate(SQLModel, table=True):
    __tablename__ = "applicant_profile_certificates"

    id:                      Optional[int] = Field(default=None, primary_key=True)
    applicant_profile_id:    int           = Field(sa_column=Column(BigInteger, ForeignKey("applicant_profiles.applicant_profile_id", ondelete="CASCADE"), nullable=False, index=True))
    issued_by:               str           = Field(max_length=50)
    certificate_url: str          = Field(max_length=255)
    name:   str           = Field(max_length=255)
    size:        str           = Field(max_length=50)
    type:        str           = Field(max_length=50)

    created_at:        datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:        datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))

    applicant_profile: Optional[ApplicantProfile] = Relationship(back_populates="certificates", sa_relationship_kwargs={"lazy": "selectin"})

class Application(SQLModel, table=True):
    __tablename__ = "applications"
    __table_args__ = (UniqueConstraint("applicant_profile_id", "job_id", name="unique_application_per_user_job"),)

    id:                   Optional[int] = Field(default=None, primary_key=True)
    application_id:       int           = Field(sa_column=Column(BigInteger, unique=True, nullable=False))
    applicant_profile_id: int           = Field(sa_column=Column(BigInteger, ForeignKey("applicant_profiles.applicant_profile_id", ondelete="CASCADE"), nullable=False, index=True))
    job_id:               int           = Field(sa_column=Column(BigInteger, ForeignKey("jobs.job_id", ondelete="CASCADE"), nullable=False, index=True))
    applied_at:           datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    status:               str           = Field(
                                              sa_column=Column(
                                                  SAEnum("applied", "viewed", "reviewed", "interview", "offer", "hired", "rejected", name="application_status"),
                                                  nullable=False, default="applied",
                                              )
                                          )
    is_rejected:          bool          = Field(default=False)
    is_top_application:   bool          = Field(default=False)
    reviewed_at:          Optional[datetime] = Field(default=None, sa_column=Column(DateTime, nullable=True))
    updated_at:           datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))

    created_at:        datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:        datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))

    applicant_profile: Optional[ApplicantProfile] = Relationship(back_populates="applications", sa_relationship_kwargs={"lazy": "selectin"})
    job:               Optional[Job]              = Relationship(back_populates="applications", sa_relationship_kwargs={"lazy": "selectin"})

class UserJobIndustry(SQLModel, table=True):
    __tablename__ = "user_job_industries"

    id:               Optional[int] = Field(default=None, primary_key=True)
    external_user_id: int           = Field(sa_column=Column(BigInteger, nullable=False, index=True))
    industry_code:    str           = Field(sa_column=Column(String(50), ForeignKey("job_industries.code", ondelete="CASCADE"), nullable=False, name="code"))

    created_at:        datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:        datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))

    industry: Optional[JobIndustry] = Relationship(back_populates="user_industries", sa_relationship_kwargs={"lazy": "selectin"})

class UserBookmarkJob(SQLModel, table=True):
    __tablename__ = "user_bookmark_jobs"
    __table_args__ = (UniqueConstraint("external_user_id", "job_id"),)

    id:               Optional[int] = Field(default=None, primary_key=True)
    external_user_id: int           = Field(sa_column=Column(BigInteger, nullable=False, index=True))
    job_id:           int           = Field(sa_column=Column(BigInteger, ForeignKey("jobs.job_id", ondelete="CASCADE"), nullable=False, name="job_id"))

    created_at:        datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:        datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))

    job: Optional[Job] = Relationship(back_populates="bookmarks", sa_relationship_kwargs={"lazy": "selectin"})

#Utils
class SalaryMarket(SQLModel, table=True):
    __tablename__ = "job_salary_markets"

    id:            Optional[int] = Field(default=None, primary_key=True)
    currency_type: str           = Field(
                                       sa_column=Column(
                                           SAEnum("INR", "USD", "EUR", "GBP", name="salary_currency"),
                                           nullable=False, default="INR",
                                       )
                                   )
    salary_start:  int           = Field(default=0)
    salary_middle: int           = Field(default=500000)
    salary_end:    int           = Field(default=1000000)

    created_at:        datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:        datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))

@event.listens_for(ApplicantProfile, "before_insert")
def before_insert_local_job(mapper, connection, target):
    session = Session(bind=connection)
 
    while True:
        new_id = random.randint(10_000_000, 99_999_999)
        exists = session.query(ApplicantProfile).filter_by(applicant_profile_id=new_id).first()
        if not exists:
            target.applicant_profile_id = new_id
            break
