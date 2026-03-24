from config import APP_NAME
from contextlib import asynccontextmanager
from database import init_db, engine
from job_database import init_job_db, job_engine

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError

from helpers.response_helper import AppException, send_error_response
from routers import (
    auth,
    app as app_module,
    board,
    profile,
    account,
    service,
    used_product_listing,
    local_job,
    job
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    print("✅ LTS360 connected & tables ready")
    yield
    await engine.dispose()
    print("🛑 LTS360 Shutting down")

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_job_db()()
    print("✅ LTS360 Jobs connected & tables ready")
    yield
    await job_engine.dispose()
    print("🛑 LTS360 Jobs Shutting down")    

@asynccontextmanager
async def lifespan(app: FastAPI):
    # await start_consumers()
    yield

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
app.include_router(service.router,      prefix="/api/v1")
app.include_router(used_product_listing.router, prefix="/api/v1")
app.include_router(local_job.router,    prefix="/api/v1")
app.include_router(job.router, prefix="/api/v1")

@app.get("/", tags=["Health"])
async def root():
    return {"status": "ok", "app": APP_NAME}

@app.get("/health", tags=["Health"])
async def health():
    return {"status": "healthy"}