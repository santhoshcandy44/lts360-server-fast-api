from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime, timezone

class Board(SQLModel, table=True):
    __tablename__ = "boards"

    board_id:    Optional[int] = Field(primary_key=True)
    board_name:  str           = Field(max_length=255)
    board_label: Optional[str] = Field(default=None, max_length=255)
    created_at:  datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at:  datetime      = Field(default_factory=lambda: datetime.now(timezone.utc))