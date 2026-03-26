from decimal import Decimal
from typing import List, Optional
from datetime import datetime, timezone
import string
import random

from sqlmodel import SQLModel, Field , Relationship
from sqlalchemy import Column, Integer, BigInteger, Numeric, ForeignKey, Enum as SAEnum, event, Index
from sqlalchemy.orm import Session
from sqlalchemy.dialects.mysql import MEDIUMINT

class Service(SQLModel, table=True):
    __tablename__ = "services"
    __table_args__ = (
        Index(
            "ft_services_title_short_description_long_description",  
            "title",
            "short_description",
            "long_description",
            mysql_prefix="FULLTEXT",            
        ),
    )
 
    id:                Optional[int] = Field(primary_key=True)
    service_id:        int           = Field(sa_column=Column(BigInteger, unique=True, nullable=False))
    title:             str           = Field(max_length=255)
    short_description: str           = Field(max_length=500)
    long_description:  str           = Field()

    industry_id: Optional[int] = Field(
        default=None,
        sa_column=Column(
            MEDIUMINT(unsigned=True),
            ForeignKey("service_industries.industry_id", ondelete="RESTRICT"),
            nullable=False,
            index=True
        )
    )

    status:            str           = Field(
                                           sa_column=Column(
                                               SAEnum("Active", "In-Review", "Rejected", "Suspended", name="service_status"),
                                               nullable=False,
                                               default="Active"
                                           )
                                       )
    short_code:        str           = Field()
   
    country_id:   int = Field(default=None, sa_column=Column(MEDIUMINT(unsigned=True), ForeignKey("countries.id", ondelete="RESTRICT"), nullable=False))
    state_id:   int = Field(default=None, sa_column=Column(MEDIUMINT(unsigned=True), ForeignKey("states.id", ondelete="RESTRICT"), nullable=False))

    created_by:        int           = Field(sa_column=Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True))
    created_at:        datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:        datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))

    thumbnail: Optional["ServiceThumbnail"] = Relationship(
            back_populates="service",
            sa_relationship_kwargs={"lazy": "selectin"}
        )
    
    images: List["ServiceImage"] = Relationship(
        back_populates="service",
        sa_relationship_kwargs={"lazy": "selectin"}
    )

    plans: List["ServicePlan"] = Relationship(
        back_populates="service",
        sa_relationship_kwargs={"lazy": "selectin"}
    )

    location: Optional["ServiceLocation"] = Relationship(
        back_populates="service",
        sa_relationship_kwargs={"lazy": "selectin"}
    )

    owner: Optional["User"] = Relationship(
        back_populates="services",
        sa_relationship_kwargs={"lazy": "selectin"}
    )

    bookmarks: List["UserBookmarkService"] = Relationship(
        back_populates="service",
        sa_relationship_kwargs={"lazy": "selectin"}
    )

    industry: Optional["ServiceIndustry"] = Relationship(
        sa_relationship_kwargs={"lazy": "selectin"}
    )

    country: Optional["Country"] = Relationship(
        sa_relationship_kwargs={"lazy": "selectin"}
    )
    
    state: Optional["State"] = Relationship(
        sa_relationship_kwargs={"lazy": "selectin"}
    )
 
class ServiceImage(SQLModel, table=True):
    __tablename__ = "service_images"

    id:         Optional[int] = Field(primary_key=True)
    service_id: int           = Field(sa_column=Column(BigInteger, ForeignKey("services.service_id", ondelete="CASCADE"), nullable=False, index=True))
    url:        str           = Field()
    width:      int           = Field()
    height:     int           = Field()
    size:       int           = Field()
    format:     str           = Field(max_length=20)
    created_at: datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))

    service: Optional["Service"] = Relationship(
        back_populates="images",        
        sa_relationship_kwargs={"lazy": "selectin"}
    )

class ServicePlan(SQLModel, table=True):
    __tablename__ = "service_plans"

    id:            Optional[int] = Field(primary_key=True)
    service_id:    int           = Field(sa_column=Column(BigInteger, ForeignKey("services.service_id", ondelete="CASCADE"), nullable=False, index=True))
    name:          str           = Field(max_length=100)
    description:   Optional[str] = Field(default=None, max_length=1000)
    price_unit:    str           = Field(max_length=20)
    price:         Decimal       = Field(sa_column=Column(Numeric(10, 2), nullable=False))
    features:      str           = Field()
    duration_unit: Optional[str] = Field(default=None, max_length=20)
    delivery_time: int           = Field()
    created_at:    datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:    datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))

    service: Optional["Service"] = Relationship(
        back_populates="plans",        
        sa_relationship_kwargs={"lazy": "selectin"}
    )

class ServiceLocation(SQLModel, table=True):
    __tablename__ = "service_locations"
 
    id:            Optional[int] = Field(primary_key=True)
    service_id:    int           = Field(sa_column=Column(BigInteger, ForeignKey("services.service_id", ondelete="CASCADE"), nullable=False, index=True))
    latitude:      Decimal       = Field(sa_column=Column(Numeric(10, 8), nullable=False))
    longitude:     Decimal       = Field(sa_column=Column(Numeric(11, 8), nullable=False))
    geo:           Optional[str] = Field(default=None)
    location_type: str           = Field(
                                       sa_column=Column(
                                           SAEnum("approximate", "precise", name="service_location_type"),
                                           nullable=False
                                       )
                                   )
    created_at:    datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:    datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))

    service: Optional["Service"] = Relationship(
        back_populates="location",        
        sa_relationship_kwargs={"lazy": "selectin"}
    )
    

class ServiceThumbnail(SQLModel, table=True):
    __tablename__ = "service_thumbnail"
 
    id: Optional[int] = Field(primary_key=True)
    service_id:   int           = Field(sa_column=Column(BigInteger, ForeignKey("services.service_id", ondelete="CASCADE"), unique=True, nullable=False))
    url:    str           = Field()
    width:        int           = Field()
    height:       int           = Field()
    size:         int           = Field()
    format:       Optional[str] = Field(default=None, max_length=20)
    created_at:   datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:   datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))

    service: Optional["Service"] = Relationship(
        back_populates="thumbnail",        
        sa_relationship_kwargs={"lazy": "selectin"}
    )

class ServiceReview(SQLModel, table=True):
    __tablename__ = "service_reviews"

    id:         Optional[int] = Field(primary_key=True)
    service_id: int           = Field(sa_column=Column(BigInteger, ForeignKey("services.service_id", ondelete="CASCADE"), nullable=False, index=True))
    user_id:    int           = Field(sa_column=Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True))
    rating:     int           = Field()
    comment:    str           = Field()
    created_at: datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))

class ServiceReviewReply(SQLModel, table=True):
    __tablename__ = "service_reviews_replies"
 
    id:                Optional[int] = Field(primary_key=True)
    user_id:           int           = Field(sa_column=Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True))
    service_review_id: int           = Field(sa_column=Column(Integer, ForeignKey("service_reviews.id", ondelete="CASCADE"), nullable=False, index=True))
    reply:             str           = Field()
    created_at:        datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:        datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))

class ServiceSearchQuery(SQLModel, table=True):
    __tablename__ = "servcie_search_queries"

    id:                       Optional[int] = Field(primary_key=True)
    search_term:              str           = Field(max_length=255, unique=True)
    search_term_concatenated: str           = Field(max_length=255, unique=True)
    popularity:               int           = Field(default=1)
    last_searched:            datetime      = Field()
    created_at:               datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:               datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))

class ServiceIndustry(SQLModel, table=True):
    __tablename__ = "service_industries"

    industry_id:   int           = Field(primary_key=True)
    industry_name: str           = Field(max_length=255)
    description:   Optional[str] = Field(default=None)
    created_at:    datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:    datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    user_service_industries: List["UserServiceIndustry"] = Relationship(
        back_populates="industry",
        sa_relationship_kwargs={"lazy": "selectin"}
    )

def _generate_short_code() -> str:
    chars = string.ascii_letters + string.digits 
    return ''.join(random.choices(chars, k=8))

@event.listens_for(Service, "before_insert")
def before_insert_local_job(mapper, connection, target):
    session = Session(bind=connection)
 
    while True:
        new_id = random.randint(10_000_000, 99_999_999)
        exists = session.query(Service).filter_by(service_id=new_id).first()
        if not exists:
            target.service_id = new_id
            break
 
    if not target.short_code:
        target.short_code = _generate_short_code()