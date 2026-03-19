from sqlmodel import SQLModel, Field
from sqlalchemy import Column, BigInteger, ForeignKey, UniqueConstraint
from typing import Optional
from datetime import datetime, timezone
 
class UserBookmarkService(SQLModel, table=True):
    __tablename__ = "user_bookmark_services"
    __table_args__ = (
        UniqueConstraint("user_id", "service_id", name="unique_user_service"),
    )
 
    id:         Optional[int] = Field(primary_key=True)
    user_id:    int           = Field(sa_column=Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False))
    service_id: int           = Field(sa_column=Column(BigInteger, ForeignKey("services.service_id", ondelete="CASCADE"), nullable=False, index=True))
    created_at: datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))



class UserBookmarkLocalJob(SQLModel, table=True):
    __tablename__ = "user_bookmark_local_jobs"
    __table_args__ = (
        UniqueConstraint("user_id", "local_job_id", name="unique_user_local_job"),
    )

    id:           Optional[int] = Field(primary_key=True)
    user_id:      int           = Field(sa_column=Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False))
    local_job_id: int           = Field(sa_column=Column(BigInteger, ForeignKey("local_jobs.local_job_id", ondelete="CASCADE"), nullable=False, index=True))
    created_at:   datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:   datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))


class UserBookmarkUsedProductListing(SQLModel, table=True):
    __tablename__ = "user_bookmark_used_product_listings"
    __table_args__ = (
        UniqueConstraint("user_id", "used_product_listing_id", name="unique_user_used_product_listing"),
    )
 
    id:                      Optional[int] = Field(primary_key=True)
    user_id:                 int           = Field(sa_column=Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False))
    used_product_listing_id: int           = Field(sa_column=Column(BigInteger, ForeignKey("used_product_listings.used_product_listing_id", ondelete="CASCADE"), nullable=False, index=True))
    created_at:              datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:              datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    
class UserIndustry(SQLModel, table=True):
    __tablename__ = "user_industries"
    __table_args__ = (
        UniqueConstraint("user_id", "industry_id", name="unique_user_industry"),
    )
 
    id:          Optional[int] = Field(primary_key=True)
    user_id:     int           = Field(sa_column=Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False))
    industry_id: int           = Field(sa_column=Column(BigInteger, ForeignKey("industries.industry_id", ondelete="CASCADE"), nullable=False, index=True))
    created_at:  datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:  datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
     