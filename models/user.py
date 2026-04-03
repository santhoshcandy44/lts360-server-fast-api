from datetime import datetime, timezone
import random
import string

from decimal import Decimal
from typing import List, Optional

from models.local_job import LocalJobApplication
from sqlmodel import SQLModel, Field, Column, Relationship
from sqlalchemy import DATETIME, Column, Integer, BigInteger, Text, ForeignKey, UniqueConstraint, Numeric, Enum as SAEnum, DateTime, UniqueConstraint, event, func, text
from sqlalchemy.orm import Session, Mapped, mapped_column

class User(SQLModel, table=True):
    __tablename__ = "users"
    id:                    Optional[int] = Field(primary_key=True)
    user_id:               int            = Field(sa_column=Column(BigInteger, unique=True, nullable=False))
    first_name:            str            = Field(max_length=100)
    last_name:             str            = Field(max_length=100)
    about:                 Optional[str]  = Field(default=None)
    profile_pic_url:       Optional[str]  = Field(default=None)
    profile_pic_url_96x96: Optional[str]  = Field(default=None)
    email:                 str            = Field(max_length=254, unique=True)
    is_email_verified:     int            = Field(default=0)
    phone_country_code:    Optional[str]  = Field(default=None, max_length=10)
    phone_number:          Optional[str]  = Field(default=None, max_length=20)
    is_phone_verified:     Optional[int]  = Field(default=0)
    account_type:          str            = Field(
                                               sa_column=Column(
                                                   SAEnum("Personal", "Business", name="account_type"),
                                                   nullable=False,
                                                   default="Personal"
                                               )
                                           )
    sign_up_method:        str            = Field(
                                               sa_column=Column(
                                                   SAEnum("legacy_email", "google", name="sign_up_method"),
                                                   nullable=False,
                                                   default="legacy_email"
                                               )
                                           )
    salt:                  str
    pepper:                str
    hashed_password:       str
    last_sign_in:          datetime       = Field(nullable=False)
    account_status:        Optional[str]  = Field(
                                               sa_column=Column(
                                                   SAEnum("active", "suspended", "deactivated", name="account_status"),
                                                   default="active"
                                               )
                                           )
    media_id:              str            = Field(max_length=32, unique=True)
    created_at:            datetime       = Field(default_factory=lambda: datetime.now(timezone.utc))

    updated_at: datetime = Field(
        sa_column=Column(
            DATETIME,
            nullable=False,
            server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")
        )
    )

    location: Optional["UserLocation"] = Relationship(
        back_populates="user",
         sa_relationship_kwargs={"lazy": "selectin"}
    )

    chat_info: Optional["ChatInfo"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"lazy": "selectin"}
    )

    fcm_token: Optional["FCMToken"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"lazy": "selectin"}
    )

    local_jobs: List["LocalJob"] = Relationship(
        back_populates="owner",         
        sa_relationship_kwargs={"lazy": "selectin"}
    )

    application: list["LocalJobApplication"] = Relationship(
        back_populates="user",
        sa_relationship_kwargs={"lazy": "selectin"}
    )
        
    used_product_listings: List["UsedProductListing"] = Relationship(
        back_populates="owner",         
        sa_relationship_kwargs={"lazy": "selectin"}
    )

    services: List["Service"] = Relationship(
        back_populates="owner",         
        sa_relationship_kwargs={"lazy": "selectin"}
    )

class UserLocation(SQLModel, table=True):
    __tablename__ = "user_locations"
 
    user_id:       int      = Field(sa_column=Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True, nullable=False))
    latitude:      Decimal  = Field(sa_column=Column(Numeric(10, 8), nullable=False))
    longitude:     Decimal  = Field(sa_column=Column(Numeric(11, 8), nullable=False))
    geo:           Optional[str] = Field(default=None)
    location_type: str      = Field(
                                  sa_column=Column(
                                      SAEnum("approximate", "precise", name="user_location_type"),
                                      nullable=False
                                  )
                              )
    created_at:    datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(
            sa_column=Column(
                DATETIME,
                nullable=False,
                server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")
            )
        )

    user: User = Relationship(back_populates="location",  sa_relationship_kwargs={"lazy": "selectin"})

 
class UserBoard(SQLModel, table=True):
    __tablename__ = "user_boards"
    __table_args__ = (
        UniqueConstraint("user_id", "board_id", name="unique_user_board"),
    )
 
    id:            Optional[int] = Field(primary_key=True)
    user_id:       int           = Field(sa_column=Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False))
    board_id:      int           = Field(sa_column=Column(Integer, ForeignKey("boards.board_id", ondelete="CASCADE"), nullable=False, index=True))
    display_order: Optional[int] = Field(default=-1)
    is_selected:   Optional[int] = Field(default=0)
    created_at:    datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(
            sa_column=Column(
                DATETIME,
                nullable=False,
                server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")
            )
        )

class UserServiceIndustry(SQLModel, table=True):
    __tablename__ = "user_service_industries"
    __table_args__ = (
        UniqueConstraint("user_id", "industry_id", name="unique_user_industry"),
    )
 
    id:          Optional[int] = Field(primary_key=True)
    user_id:     int           = Field(sa_column=Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False))
    industry_id: int           = Field(sa_column=Column(Integer, ForeignKey("service_industries.industry_id", ondelete="CASCADE"), nullable=False, index=True))
    created_at:  datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(
            sa_column=Column(
                DATETIME,
                nullable=False,
                server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")
            )
        )

    industry: Optional["ServiceIndustry"] = Relationship(
        back_populates="user_service_industries",
        sa_relationship_kwargs={"lazy": "selectin"}
    )
             
class FCMToken(SQLModel, table=True):
    __tablename__ = "fcm_tokens"
 
    id:         Optional[int] = Field(primary_key=True)
    user_id:    int           = Field(sa_column=Column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE"), unique=True, nullable=False))
    fcm_token:  Optional[str] = Field(sa_column=Column(Text))  
    created_at: datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(
            sa_column=Column(
                DATETIME,
                nullable=False,
                server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")
            )
        )

    user: Optional["User"] = Relationship(
        back_populates="fcm_token",
        sa_relationship_kwargs={"lazy": "selectin"}
    ) 

def _generate_short_code() -> str:
    chars = string.ascii_letters + string.digits 
    return ''.join(random.choices(chars, k=6))

@event.listens_for(User, "before_insert")
def before_insert_local_job(mapper, connection, target):
    session = Session(bind=connection)
 
    while True:
        new_id = random.randint(10_000_000, 99_999_999)
        exists = session.query(User).filter_by(user_id=new_id).first()
        if not exists:
            target.user_id = new_id
            break
 
    if not target.media_id:
        target.media_id = _generate_short_code()