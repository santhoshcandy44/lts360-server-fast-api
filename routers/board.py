from fastapi import APIRouter, Depends, Request
from middleware.auth_middleware import authenticate_token
from schemas.board_schemas import UpdateBoardsRequest

router = APIRouter(
    prefix="/boards",
    tags=["Boards"],
)


@router.get("/")
async def get_boards(
    request: Request,
    current_user=Depends(authenticate_token),   # 👈 protected
):
    pass


@router.get("/guest")
async def guest_get_boards(request: Request):   # 👈 no auth
    pass


@router.put("/")
async def update_boards(
    body:         UpdateBoardsRequest,
    request:      Request,
    current_user=Depends(authenticate_token),   # 👈 protected
):
    pass