
from fastapi import APIRouter, Depends

router = APIRouter(
    prefix="/users",   
    tags=["Users"],
)

@router.get("/")
def list_users():
    return {"message": "list of users"}

@router.get("/{user_id}")
def get_user(user_id: int):
    return {"user_id": user_id}

@router.post("/")
def create_user():
    return {"message": "user created"}