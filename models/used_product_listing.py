from datetime import datetime, timezone
import string
import random

from decimal import Decimal
from typing import List, Optional

from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, BigInteger, ForeignKey, Numeric, Enum as SAEnum, Index, event
from sqlalchemy.orm import Session
from sqlalchemy.dialects.mysql import MEDIUMINT

class UsedProductListing(SQLModel, table=True):
    __tablename__ = "used_product_listings"
    __table_args__ = (
        Index(
            "ft_local_jobs_name_description",  
            "name",
            "description",
            mysql_prefix="FULLTEXT",            
        ),
    )

    id:                       Optional[int] = Field(primary_key=True)
    used_product_listing_id:  int           = Field(sa_column=Column(BigInteger, unique=True, nullable=False))
    name:                     str           = Field(max_length=255)
    description:              str           = Field()
    price_unit:               str           = Field(max_length=20)
    price:                    Decimal       = Field(sa_column=Column(Numeric(10, 2), nullable=False))
    status:                   str           = Field(
                                                  sa_column=Column(
                                                      SAEnum("Active", "In-Review", "Rejected", name="used_product_status"),
                                                      nullable=False,
                                                      default="Active"
                                                  )
                                              )
    short_code:               str           = Field()
    
    country_id:   int = Field(default=None, sa_column=Column(MEDIUMINT(unsigned=True), ForeignKey("countries.id", ondelete="RESTRICT"), nullable=False))
    state_id:   int = Field(default=None, sa_column=Column(MEDIUMINT(unsigned=True), ForeignKey("states.id", ondelete="RESTRICT"), nullable=False))

    created_by:               int           = Field(sa_column=Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False, index=True))
    created_at:               datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:               datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))

    images: List["UsedProductListingImage"] = Relationship(
        back_populates="used_prodct_listing",
        sa_relationship_kwargs={"lazy": "selectin"}
    )

    location: Optional["UsedProductListingLocation"] = Relationship(
        back_populates="used_prodct_listing",
        sa_relationship_kwargs={"lazy": "selectin"}
    )

    owner: Optional["User"] = Relationship(
        back_populates="used_product_listings",
        sa_relationship_kwargs={"lazy": "selectin"}
    )

    bookmarks: List["UserBookmarkUsedProductListing"] = Relationship(
        back_populates="used_product_listing",
        sa_relationship_kwargs={"lazy": "selectin"}
    )

    country: Optional["Country"] = Relationship(
        sa_relationship_kwargs={"lazy": "selectin"}
    )
    
    state: Optional["State"] = Relationship(
        sa_relationship_kwargs={"lazy": "selectin"}
    )

class UsedProductListingImage(SQLModel, table=True):
    __tablename__ = "used_product_listing_images"
 
    id:                      Optional[int] = Field(primary_key=True)
    used_product_listing_id: int           = Field(sa_column=Column(BigInteger, ForeignKey("used_product_listings.used_product_listing_id", ondelete="CASCADE"), nullable=False, index=True))
    url:                    str           = Field()
    width:                   int           = Field()
    height:                  int           = Field()
    size:                    int           = Field()
    format:                  str           = Field(max_length=20)
    created_at:              datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:              datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))

    used_prodct_listing: Optional["UsedProductListing"] = Relationship(
        back_populates="images",        
        sa_relationship_kwargs={"lazy": "selectin"}
    )

    
class UsedProductListingLocation(SQLModel, table=True):
    __tablename__ = "used_product_listing_locations"
 
    id:                      Optional[int] = Field(primary_key=True)
    used_product_listing_id: int           = Field(sa_column=Column(BigInteger, ForeignKey("used_product_listings.used_product_listing_id", ondelete="CASCADE"), nullable=False, index=True))
    latitude:                Decimal       = Field(sa_column=Column(Numeric(10, 8), nullable=False))
    longitude:               Decimal       = Field(sa_column=Column(Numeric(11, 8), nullable=False))
    geo:                     Optional[str] = Field(default=None)
    location_type:           str           = Field(
                                                sa_column=Column(
                                                    SAEnum("approximate", "precise", name="used_product_location_type"),
                                                    nullable=False
                                                )
                                            )
    created_at:              datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:              datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))

    used_prodct_listing: Optional["UsedProductListing"] = Relationship(
        back_populates="location",       
        sa_relationship_kwargs={"lazy": "selectin"}
    )

class UsedProductListingSearchQuery(SQLModel, table=True):
    __tablename__ = "used_product_listing_search_queries"
 
    id:                       Optional[int] = Field(primary_key=True)
    search_term:              str           = Field(max_length=255, unique=True)
    search_term_concatenated: Optional[str] = Field(max_length=255, unique=True)
    popularity:               int           = Field(default=1)
    last_searched:            datetime      = Field()
    created_at:               datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:               datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))

def _generate_short_code() -> str:
    chars = string.ascii_letters + string.digits 
    return ''.join(random.choices(chars, k=8))

@event.listens_for(UsedProductListing, "before_insert")
def before_insert_local_job(mapper, connection, target):
    session = Session(bind=connection)
 
    while True:
        new_id = random.randint(10_000_000, 99_999_999)
        exists = session.query(UsedProductListing).filter_by(used_product_listing_id=new_id).first()
        if not exists:
            target.used_product_listing_id = new_id
            break
 
    if not target.short_code:
        target.short_code = _generate_short_code()

      