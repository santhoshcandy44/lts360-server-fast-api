# routers/local_jobs.py
from fastapi import APIRouter, Depends, Request, Query, UploadFile, File
from typing import Optional, List
from middleware.auth_middleware import authenticate_token
from schemas.local_job_schemas import CreateLocalJobRequest

router = APIRouter(
    prefix="/local-jobs",
    tags=["Local Jobs"],
)


# ── Guest routes (no auth) ────────────────────────────────────────────────────

@router.get("/guest")
async def guest_get_local_jobs(
    request:   Request,
    s:         Optional[str]   = Query(default=None, max_length=100),
    latitude:  Optional[float] = Query(default=None, ge=-90,  le=90),
    longitude: Optional[float] = Query(default=None, ge=-180, le=180),
    page_size: Optional[int]   = Query(default=None),
    next_token: Optional[str]  = Query(default=None),
):
    pass


@router.get("/guest/search-suggestions")
async def guest_local_jobs_search_suggestion(
    request: Request,
    query:   str = Query(..., min_length=1),
):
    pass


@router.get("/guest/{local_job_id}")
async def guest_get_local_job(
    local_job_id: int,
    request:      Request,
):
    pass


# ── Protected routes ──────────────────────────────────────────────────────────

@router.get("/search-suggestions")
async def local_jobs_search_suggestion(
    request:      Request,
    query:        str = Query(..., min_length=1),
    current_user=Depends(authenticate_token),
):
    pass


@router.get("/me")
async def get_me_local_jobs(
    request:    Request,
    page_size:  Optional[int] = Query(default=None),
    next_token: Optional[str] = Query(default=None),
    current_user=Depends(authenticate_token),
):
    pass


@router.get("/")
async def get_local_jobs(
    request:    Request,
    s:          Optional[str] = Query(default=None, max_length=100),
    page_size:  Optional[int] = Query(default=None),
    next_token: Optional[str] = Query(default=None),
    current_user=Depends(authenticate_token),
):
    pass


@router.get("/{local_job_id}")
async def get_local_job(
    local_job_id: int,
    request:      Request,
    current_user=Depends(authenticate_token),
):
    pass


@router.post("/")
async def create_or_update_local_job(
    request:      Request,
    body:         CreateLocalJobRequest,
    images:       Optional[List[UploadFile]] = File(default=None),
    current_user=Depends(authenticate_token),
):
    pass


@router.post("/{local_job_id}/apply")
async def apply_local_job(
    local_job_id: int,
    request:      Request,
    current_user=Depends(authenticate_token),
):
    pass


@router.delete("/{local_job_id}")
async def delete_local_job(
    local_job_id: int,
    request:      Request,
    current_user=Depends(authenticate_token),
):
    pass


@router.get("/{local_job_id}/applications")
async def get_local_job_applications(
    local_job_id: int,
    request:      Request,
    page_size:    Optional[int] = Query(default=None),
    next_token:   Optional[str] = Query(default=None),
    current_user=Depends(authenticate_token),
):
    pass


@router.post("/{local_job_id}/applications/{application_id}/review")
async def mark_as_reviewed_local_job(
    local_job_id:   int,
    application_id: int,
    request:        Request,
    current_user=Depends(authenticate_token),
):
    pass


@router.delete("/{local_job_id}/applications/{application_id}/review")
async def unmark_reviewed_local_job(
    local_job_id:   int,
    application_id: int,
    request:        Request,
    current_user=Depends(authenticate_token),
):
    pass


@router.post("/{local_job_id}/bookmark")
async def bookmark_local_job(
    local_job_id: int,
    request:      Request,
    current_user=Depends(authenticate_token),
):
    pass


@router.delete("/{local_job_id}/bookmark")
async def unbookmark_local_job(
    local_job_id: int,
    request:      Request,
    current_user=Depends(authenticate_token),
):
    pass