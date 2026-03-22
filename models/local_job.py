from decimal import Decimal
import random
from typing import List, Optional
from datetime import datetime, timezone
import string

from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, BigInteger, ForeignKey, Numeric, Enum as SAEnum, event, Index
from sqlalchemy.orm import Session

class LocalJob(SQLModel, table=True):
    __tablename__ = "local_jobs"
    __table_args__ = (
        Index(
            "ft_local_jobs_title_description",  
            "title",
            "description",
            mysql_prefix="FULLTEXT",            
        ),
    )
 
    id:               Optional[int] = Field(primary_key=True)
    local_job_id:     int           = Field(sa_column=Column(BigInteger, unique=True, nullable=False))
    title:            str           = Field(max_length=255)
    description:      str           = Field()
    company:          str           = Field(max_length=255)
    age_min:          int           = Field()
    age_max:          int           = Field()
    marital_statuses: str           = Field()
    salary_unit:      str           = Field(max_length=20)
    salary_min:       int           = Field()
    salary_max:       int           = Field()
    status:           str           = Field(
                                          sa_column=Column(
                                              SAEnum("Active", "In-Review", "Rejected", name="local_job_status"),
                                              nullable=False,
                                              default="Active"
                                          )
                                      )
    short_code:       str           = Field()
    country:          str           = Field(max_length=255)
    state:            str           = Field(max_length=255)
    created_by:       int           = Field(sa_column=Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False))
    created_at:       datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:       datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))

    images: List["LocalJobImage"] = Relationship(
        back_populates="local_job",
        sa_relationship_kwargs={"lazy": "selectin"}
    )

    location: Optional["LocalJobLocation"] = Relationship(
        back_populates="local_job",
        sa_relationship_kwargs={"lazy": "selectin"}
    )

    owner: Optional["User"] = Relationship(
        back_populates="local_jobs",
        sa_relationship_kwargs={"lazy": "selectin"}
    )

    applications: List["LocalJobApplication"] = Relationship(back_populates="local_job", sa_relationship_kwargs={"lazy": "selectin"})

    bookmarks: List["UserBookmarkLocalJob"] = Relationship(
        back_populates="local_job",
        sa_relationship_kwargs={"lazy": "selectin"}
    )

class LocalJobImage(SQLModel, table=True):
    __tablename__ = "local_job_images"
 
    id:           Optional[int] = Field(primary_key=True)
    local_job_id: int           = Field(sa_column=Column(BigInteger, ForeignKey("local_jobs.local_job_id", ondelete="CASCADE"), nullable=False))
    url:          str           = Field()
    width:        int           = Field()
    height:       int           = Field()
    size:         int           = Field()
    format:       Optional[str] = Field(default=None, max_length=20)
    created_at:   datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:   datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))

    local_job: Optional["LocalJob"] = Relationship(
        back_populates="images",        
        sa_relationship_kwargs={"lazy": "selectin"}
    )


class LocalJobLocation(SQLModel, table=True):
    __tablename__ = "local_job_location"
 
    id:            Optional[int] = Field(primary_key=True)
    local_job_id:  int           = Field(sa_column=Column(BigInteger, ForeignKey("local_jobs.local_job_id", ondelete="CASCADE"), nullable=False))
    latitude:      Decimal        = Field(sa_column=Column(Numeric(10, 8), nullable=False))
    longitude:     Decimal        = Field(sa_column=Column(Numeric(11, 8), nullable=False))
    geo:           Optional[str] = Field(default=None)
    location_type: str           = Field(
                                       sa_column=Column(
                                           SAEnum("approximate", "precise", name="location_type"),
                                           nullable=False
                                       )
                                   )
    created_at:    datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:    datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))


    local_job: Optional["LocalJob"] = Relationship(
        back_populates="location",       
        sa_relationship_kwargs={"lazy": "selectin"}
    )


class LocalJobSearchQuery(SQLModel, table=True):
    __tablename__ = "local_job_search_queries"

    id:                       Optional[int] = Field(primary_key=True)
    search_term:              str           = Field(max_length=255, unique=True)
    search_term_concatenated: str           = Field(max_length=255, unique=True)
    popularity:               int           = Field(default=1)
    last_searched:            datetime      = Field()
    created_at:               datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:               datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
 
class LocalJobApplication(SQLModel, table=True):
    __tablename__ = "local_job_applications"

    id:             int           = Field(sa_column=Column(BigInteger, primary_key=True, autoincrement=True))
    application_id: int           = Field(sa_column=Column(BigInteger, nullable=False))
    local_job_id:   int           = Field(sa_column=Column(BigInteger, ForeignKey("local_jobs.local_job_id", ondelete="CASCADE"), nullable=False))
    candidate_id:   int           = Field(sa_column=Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False))
    applied_at:     datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_reviewed:    int           = Field(default=0)
    reviewed_at:    Optional[datetime] = Field(default=None)
    created_at:     datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:     datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))

    user: "User" = Relationship(back_populates="application", sa_relationship_kwargs={"lazy": "selectin"})
    local_job: "LocalJob" = Relationship(back_populates="applications", sa_relationship_kwargs={"lazy": "selectin"})

def _generate_short_code() -> str:
    chars = string.ascii_letters + string.digits 
    return ''.join(random.choices(chars, k=8))

@event.listens_for(LocalJob, "before_insert")
def before_insert_local_job(mapper, connection, target):
    session = Session(bind=connection)
 
    while True:
        new_id = random.randint(10_000_000, 99_999_999)
        exists = session.query(LocalJob).filter_by(local_job_id=new_id).first()
        if not exists:
            target.local_job_id = new_id
            break
 
    if not target.short_code:
        target.short_code = _generate_short_code()


@event.listens_for(LocalJobApplication, "before_insert")
def before_insert_local_job_application(mapper, connection, target):
    session = Session(bind=connection)
 
    while True:
        new_id = random.randint(10_000_000, 99_999_999)
        exists = session.query(LocalJobApplication).filter_by(application_id=new_id).first()
        if not exists:
            target.application_id = new_id
            break       