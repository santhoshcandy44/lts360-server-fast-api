from decimal import Decimal
from typing import List, Optional
from datetime import datetime, timezone

from sqlalchemy import (DATETIME, Column , Numeric, String, text)
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy.dialects.mysql import MEDIUMINT

class Board(SQLModel, table=True):
    __tablename__ = "boards"

    board_id:    Optional[int] = Field(primary_key=True)
    board_name:  str           = Field(max_length=255)
    board_label: Optional[str] = Field(default=None, max_length=255)
    created_at:  datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(
            sa_column=Column(
                DATETIME,
                nullable=False,
                server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP")
            )
        )
    
class Country(SQLModel, table=True):
    __tablename__ = "countries"
    __table_args__ = {"extend_existing": True}

    id:   int = Field(sa_column=Column(MEDIUMINT(unsigned=True), primary_key=True))
    name: str = Field(max_length=100)
    iso2: str = Field(max_length=2, sa_column=Column(String(2), unique=True))

    organizations: List["Organization"] = Relationship(
        back_populates="country",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    settings: Optional["RecruiterSettings"] = Relationship(
        back_populates="country",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

class State(SQLModel, table=True):
    __tablename__ = "states"
    __table_args__ = {"extend_existing": True}

    id:         int = Field(sa_column=Column(MEDIUMINT(unsigned=True), primary_key=True))
    name:       str = Field(max_length=100)
    iso2:       str = Field(max_length=2, sa_column=Column(String(2), unique=True))
    country_id: int = Field(sa_column=Column(MEDIUMINT(unsigned=True), nullable=False))

    organizations: List["Organization"] = Relationship(
        back_populates="state",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

class City(SQLModel, table=True):
    __tablename__ = "cities"
    __table_args__ = {"extend_existing": True}

    id:         int = Field(sa_column=Column(MEDIUMINT(unsigned=True), primary_key=True))
    name:       str = Field(max_length=100)
    country_id: int = Field(sa_column=Column(MEDIUMINT(unsigned=True), nullable=False))
    state_id:   int = Field(sa_column=Column(MEDIUMINT(unsigned=True), nullable=False))
    latitude:      Decimal        = Field(sa_column=Column(Numeric(10, 8), nullable=False))
    longitude:     Decimal        = Field(sa_column=Column(Numeric(11, 8), nullable=False))

    jobs: List["Job"] = Relationship(
        back_populates="city",
        sa_relationship_kwargs={"lazy": "selectin"},
    )

    organizations: List["Organization"] = Relationship(
        back_populates="city",
        sa_relationship_kwargs={"lazy": "selectin"},
    )    