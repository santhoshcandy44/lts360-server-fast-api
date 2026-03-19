from fastapi import Request

from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.mysql import insert

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
 
async def get_boards(request: Request, db: AsyncSession):
    try:
        user_id = request.state.user.user_id

        result = await db.execute(
            select(
                Board.board_id,
                Board.board_name,
                Board.board_label,
                UserBoard.display_order,
                UserBoard.user_id,
            )
            .outerjoin(UserBoard, (UserBoard.board_id == Board.board_id) & (UserBoard.user_id == user_id))
        )
        rows = result.fetchall()

        boards = [
            {
                "board_id":      row.board_id,
                "board_name":    row.board_name,
                "board_label":   row.board_label,
                "display_order": row.display_order if row.display_order is not None else -1,
                "is_selected":   bool(row.user_id),
            }
            for row in rows
        ]

        return send_json_response(200, "Boards fetched successfully", data=boards)
    except Exception:
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

async def update_boards(request: Request, body, db: AsyncSession):
    try:
        user_id = request.state.user.user_id

        for board in body.boards:
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

        result = await db.execute(
            select(
                Board.board_id,
                Board.board_name,
                Board.board_label,
                UserBoard.display_order,
                UserBoard.user_id,
            )
            .outerjoin(UserBoard, (UserBoard.board_id == Board.board_id) & (UserBoard.user_id == user_id))
        )
        rows = result.fetchall()

        boards = [
            {
                "board_id":      row.board_id,
                "board_name":    row.board_name,
                "board_label":   row.board_label,
                "display_order": row.display_order if row.display_order is not None else -1,
                "is_selected":   bool(row.user_id),
            }
            for row in rows
        ]
        
        return send_json_response(200, "Boards updated successfully", data=boards)
    except Exception:
        return send_error_response(request, 500, "Internal server error")