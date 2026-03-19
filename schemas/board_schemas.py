from pydantic import BaseModel, field_validator
from typing import Optional, List
import json


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
    boards: str

    @field_validator("boards")
    def validate_boards(cls, v):
        if not isinstance(v, str):
            raise ValueError("Boards must be a valid JSON string")
        try:
            boards_array = json.loads(v)
        except Exception:
            raise ValueError("Boards must be a valid JSON string")

        if not isinstance(boards_array, list):
            raise ValueError("Boards must be an array")

        is_any_selected = any(board.get("is_selected") is True for board in boards_array)
        if not is_any_selected:
            raise ValueError("At least one board must be selected")

        for board in boards_array:
            if not isinstance(board.get("board_id"), int) or not isinstance(board.get("is_selected"), bool):
                raise ValueError("Each board must have a valid board_id and is_selected field")
            if board.get("industry_name") is not None and not isinstance(board.get("industry_name"), str):
                raise ValueError("Each board must have a valid board_name (if present)")
            if board.get("industry_name") is not None and not isinstance(board.get("industry_label"), str):
                raise ValueError("Each board must have a valid board_label (if present)")

        return v