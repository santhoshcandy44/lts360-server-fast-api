
from fastapi import APIRouter

router = APIRouter(
    prefix="/auth",    # all routes here start with /auth
    tags=["Auth"],
)

@router.post("/login")
def login():
    return {"message": "logged in"}

@router.post("/logout")
def logout():
    return {"message": "logged out"}

@router.post("/register")
def register():
    return {"message": "registered"}