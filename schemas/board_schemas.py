# schemas/board_schemas.py
from pydantic import BaseModel, field_validator
from typing import Optional, List


class BoardItem(BaseModel):
    board_id:       int
    is_selected:    bool
    industry_name:  Optional[str] = None
    industry_label: Optional[str] = None


class UpdateBoardsRequest(BaseModel):
    boards: List[BoardItem]

    @field_validator("boards")
    def validate_boards(cls, v):
        if not any(board.is_selected for board in v):
            raise ValueError("At least one board must be selected")
        return v