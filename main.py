from config import APP_NAME
from contextlib import asynccontextmanager
from database import init_db
import FastAPI

from routers import (
    auth,
    account,
    app,
    board,
    profile,
    local_jobs,
    services,
    used_product_listing,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    print("✅ MySQL connected & tables ready")
    yield
    print("🛑 Shutting down")


application = FastAPI(title=APP_NAME, lifespan=lifespan)

application.include_router(auth.router,          prefix="/api/v1")
application.include_router(app.router,           prefix="/api/v1")
application.include_router(board.router,        prefix="/api/v1")
application.include_router(profile.router,       prefix="/api/v1")
application.include_router(account.router,       prefix="/api/v1")
application.include_router(services.router,      prefix="/api/v1")
application.include_router(local_jobs.router,    prefix="/api/v1")
application.include_router(used_product_listing.router, prefix="/api/v1")

@application.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "app": APP_NAME}

@application.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy"}