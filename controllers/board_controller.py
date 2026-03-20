from fastapi import Request

from schemas.board_schemas import UpdateBoardsSchema
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.orm import selectinload

from models.common import Board
from models.users import UserBoard
from helpers.response_helper import send_json_response, send_error_response

async def create_default_boards_for_user(user_id: int, db: AsyncSession):
    result = await db.execute(select(Board))
    rows   = result.scalars().all()
 
    if not rows:
        raise Exception("No boards are available")
 
    default_labels = {"services": 0, "second_hands": 1, "local_jobs": 2}
 
    for row in rows:
        if row.board_label not in default_labels:
            continue
        display_order = default_labels[row.board_label]
        stmt = insert(UserBoard).values(
            user_id=user_id,
            board_id=row.board_id,
            display_order=display_order,
            is_selected=1,
        )
        stmt = stmt.on_duplicate_key_update(display_order=stmt.inserted.display_order)
        await db.execute(stmt)
 
    await db.flush()

async def get_boards_by_user_id(request: Request, user_id: int,  db: AsyncSession):
    try:
        all_boards = (await db.execute(
            select(Board)
        )).scalars().all()

        user_boards = (await db.execute(
            select(UserBoard).where(UserBoard.user_id == user_id)
        )).scalars().all()

        user_board_map = {ub.board_id: ub for ub in user_boards}

        boards = [
            {
                "board_id":      board.board_id,
                "board_name":    board.board_name,
                "board_label":   board.board_label,
                "is_selected":   board.board_id in user_board_map,
                "display_order": user_board_map[board.board_id].display_order
                                 if board.board_id in user_board_map else -1,
            }
            for board in all_boards
        ]

        return boards
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def get_boards(request: Request, db: AsyncSession):
    try:
        user_id = request.state.user.user_id

        all_boards = (await db.execute(
            select(Board)
        )).scalars().all()

        user_boards = (await db.execute(
            select(UserBoard).where(UserBoard.user_id == user_id)
        )).scalars().all()

        user_board_map = {ub.board_id: ub for ub in user_boards}

        boards = [
            {
                "board_id":      board.board_id,
                "board_name":    board.board_name,
                "board_label":   board.board_label,
                "is_selected":   board.board_id in user_board_map,
                "display_order": user_board_map[board.board_id].display_order
                                 if board.board_id in user_board_map else -1,
            }
            for board in all_boards
        ]

        return send_json_response(200, "Boards fetched successfully", data=boards)
    except Exception:
        import traceback
        import sys
        traceback.print_exc(file=sys.stderr)
        sys.stderr.flush()
        return send_error_response(request, 500, "Internal server error")

async def guest_get_boards(request: Request, db: AsyncSession):
    try:
        result = await db.execute(select(Board))
        rows   = result.scalars().all()

        label_order    = {"services": 0, "second_hands": 1, "local_jobs": 2, "jobs": 3}
        selected_labels = {"services", "second_hands", "local_jobs", "jobs"}

        boards = [
            {
                "board_id":      row.board_id,
                "board_name":    row.board_name,
                "board_label":   row.board_label,
                "display_order": label_order.get(row.board_label, -1),
                "is_selected":   row.board_label in selected_labels,
            }
            for row in rows
        ]

        return send_json_response(200, "Boards fetched successfully", data=boards)
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def update_boards(request: Request, schema:UpdateBoardsSchema, db: AsyncSession):
    try:
        user_id = request.state.user.user_id

        for board in schema.boards:
            if board.is_selected:
                stmt = insert(UserBoard).values(
                    user_id=user_id,
                    board_id=board.board_id,
                    display_order=board.display_order if hasattr(board, "display_order") else -1,
                )
                stmt = stmt.on_duplicate_key_update(display_order=stmt.inserted.display_order)
                await db.execute(stmt)
            else:
                existing = await db.execute(
                    select(UserBoard).where(
                        UserBoard.user_id == user_id,
                        UserBoard.board_id == board.board_id,
                    )
                )
                user_board = existing.scalar_one_or_none()
                if user_board:
                    await db.delete(user_board)

        await db.flush()

        all_boards = (await db.execute(
            select(Board)
        )).scalars().all()

        user_boards = (await db.execute(
            select(UserBoard).where(UserBoard.user_id == user_id)
        )).scalars().all()

        user_board_map = {ub.board_id: ub for ub in user_boards}

        boards = [
            {
                "board_id":      board.board_id,
                "board_name":    board.board_name,
                "board_label":   board.board_label,
                "is_selected":   board.board_id in user_board_map,
                "display_order": user_board_map[board.board_id].display_order
                                 if board.board_id in user_board_map else -1,
            }
            for board in all_boards
        ]
        
        return send_json_response(200, "Boards updated successfully", data=boards)
    except Exception:
        import traceback
        import sys
        traceback.print_exc(file=sys.stderr)
        sys.stderr.flush()
        return send_error_response(request, 500, "Internal server error")