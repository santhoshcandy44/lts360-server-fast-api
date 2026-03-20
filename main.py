from pydantic import ValidationError

from config import APP_NAME
from contextlib import asynccontextmanager
from database import init_db, engine
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError

from helpers.response_helper import AppException, send_error_response
from routers import (
    auth,
    account,
    app as app_module,
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
    await engine.dispose()
    print("🛑 Shutting down")

app = FastAPI(title=APP_NAME, lifespan=lifespan)

@app.exception_handler(AppException)
async def valdiate_app_exception_handler(request: Request, exc: AppException):
    return send_error_response(request, exc.status_code, exc.message, exc.error_code)

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    if errors:
        first_error = errors[0]
        field   = " -> ".join(str(loc) for loc in first_error["loc"] if loc != "body")
        message = first_error["msg"]
        detail  = f"{field}: {message}" if field else message
    else:
        detail = "Invalid request"

    return send_error_response(
        request=request,
        status_code=422,
        message=detail,
        error_details=errors or None,
        error_code="VALIDATION_ERROR",
    )

app.include_router(auth.router,          prefix="/api/v1")
app.include_router(app_module.router,           prefix="/api/v1")
app.include_router(board.router,        prefix="/api/v1")
app.include_router(profile.router,       prefix="/api/v1")
app.include_router(account.router,       prefix="/api/v1")
app.include_router(services.router,      prefix="/api/v1")
app.include_router(local_jobs.router,    prefix="/api/v1")
app.include_router(used_product_listing.router, prefix="/api/v1")

@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "app": APP_NAME}

@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy"}