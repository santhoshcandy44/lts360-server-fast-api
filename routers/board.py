from database import get_db
from .middleware.auth_middleware import authenticate_token

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from schemas.board_schemas import UpdateBoardsSchema
from controllers import board_controller

router = APIRouter(
    prefix="/boards",
    tags=["Boards"],
)


@router.get("")
async def get_boards(
    request: Request,
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await board_controller.get_boards(request, db)


@router.get("/guest")
async def guest_get_boards(
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    return await board_controller.guest_get_boards(request, db)


@router.put("")
async def update_boards(
    schema:    UpdateBoardsSchema,
    request: Request,
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await board_controller.update_boards(request, schema, db)