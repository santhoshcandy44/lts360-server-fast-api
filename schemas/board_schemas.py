from pydantic import BaseModel, field_validator
from typing import Optional, List


class Board(BaseModel):
    board_id:       int
    is_selected:    bool
    industry_name:  Optional[str] = None
    industry_label: Optional[str] = None

    @field_validator("board_id")
    def validate_board_id(cls, v):
        if not isinstance(v, int):
            raise ValueError("Each board must have a valid board_id")
        return v

    @field_validator("industry_name")
    def validate_industry_name(cls, v):
        if v is not None and not isinstance(v, str):
            raise ValueError("Each board must have a valid board_name (if present)")
        return v

    @field_validator("industry_label")
    def validate_industry_label(cls, v):
        if v is not None and not isinstance(v, str):
            raise ValueError("Each board must have a valid board_label (if present)")
        return v


class UpdateBoardsRequest(BaseModel):
    boards: List[Board]

    @field_validator("boards")
    def validate_boards(cls, v):
        if not isinstance(v, list):
            raise ValueError("Boards must be an array")

        is_any_selected = any(board.get("is_selected") is True for board in v)
        if not is_any_selected:
            raise ValueError("At least one board must be selected")
        
        return v