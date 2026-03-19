# main.py
from contextlib import asynccontextmanager

from database import init_db
from fastapi import FastAPI
from routers import users, auth
from config import APP_NAME

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()   # creates all tables on startup
    print("✅ MySQL connected & tables ready")
    yield
    print("🛑 Shutting down")
    
app = FastAPI(title = APP_NAME, lifespan = lifespan)

app.include_router(auth.router,  prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")

@app.get("/")
def root():
    return {"message": "API is running"}

