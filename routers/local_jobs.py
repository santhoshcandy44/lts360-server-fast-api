from database import get_db
from .middleware.auth_middleware import authenticate_token

from fastapi import APIRouter, Depends, Request, Path, Form
from sqlalchemy.ext.asyncio import AsyncSession

from schemas.local_job_schemas import (
    GetLocalJobsbSchema, 
    GuestGetLocalJobsSchema,
    LocalJobApplicationParam,
    GetLocalJobApplicationsRequest,
    CreateOrUpdateLocalJobSchema,
    GetMeLocalJobsSchema,
    SearchSuggestionsRequest,
    LocalJobIdSchema,
    create_or_update_local_job_form
)

from controllers import local_job_controller

router = APIRouter(
    prefix="/local-jobs",
    tags=["Local Jobs"],
)

@router.get("/guest/search-suggestions")
async def guest_local_jobs_search_suggestion(
    request: Request,
    params:  SearchSuggestionsRequest = Depends(),
    db:      AsyncSession = Depends(get_db),
):
    return await local_job_controller.local_jobs_search_suggestion(request, params, db)


@router.get("/guest")
async def guest_get_local_jobs(
    request: Request,
    params:  GuestGetLocalJobsSchema = Depends(),
    db:      AsyncSession = Depends(get_db),
):
    return await local_job_controller.guest_get_local_jobs(request, params, db)


@router.get("/guest/{local_job_id}")
async def guest_get_local_job(
    request:      Request,
    local_job_id: int = Path(..., ge=1),
    db:           AsyncSession = Depends(get_db),
):
    return await local_job_controller.guest_get_local_job(request, local_job_id, db)


@router.get("/search-suggestions")
async def local_jobs_search_suggestion(
    request: Request,
    params:  SearchSuggestionsRequest = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await local_job_controller.local_jobs_search_suggestion(request, params, db)


@router.get("/me")                               
async def get_me_local_jobs(
    request: Request,
    params:  GetMeLocalJobsSchema = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await local_job_controller.get_me_local_jobs(request, params, db)


@router.get("")
async def get_local_jobs(
    request: Request,
    params:  GetLocalJobsbSchema = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await local_job_controller.get_local_jobs(request, params, db)


@router.post("")
async def create_or_update_local_job(
    request: Request,
    schema:  CreateOrUpdateLocalJobSchema = Depends(create_or_update_local_job_form),
    db:      AsyncSession                 = Depends(get_db),
    _:       None                         = Depends(authenticate_token),
):
    return await local_job_controller.create_or_update_local_job(request, schema, db)


@router.get("/{local_job_id}")                   
async def get_local_job(
    request:      Request,
    local_job_id: int = Path(..., ge=1),
    db:           AsyncSession = Depends(get_db),
    _:            None = Depends(authenticate_token),
):
    return await local_job_controller.get_local_job(request, local_job_id, db)


@router.post("/{local_job_id}/apply")
async def apply_local_job(
    request: Request,
    params:  LocalJobIdSchema = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await local_job_controller.apply_local_job(request, params, db)


@router.delete("/{local_job_id}")
async def delete_local_job(
    request: Request,
    params:  LocalJobIdSchema = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await local_job_controller.delete_local_job(request, params, db)


@router.get("/{local_job_id}/applications")
async def get_local_job_applications(
    request: Request,
    params:  GetLocalJobApplicationsRequest = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await local_job_controller.get_local_job_applications(request, params, db)


@router.post("/{local_job_id}/applications/{application_id}/review")
async def mark_as_reviewed_local_job(
    request: Request,
    params:  LocalJobApplicationParam = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await local_job_controller.mark_as_reviewed_local_job(request, params, db)


@router.delete("/{local_job_id}/applications/{application_id}/review")
async def unmark_reviewed_local_job(
    request: Request,
    params:  LocalJobApplicationParam = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await local_job_controller.unmark_reviewed_local_job(request, params, db)


@router.post("/{local_job_id}/bookmark")
async def bookmark_local_job(
    request: Request,
    params:  LocalJobIdSchema = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await local_job_controller.bookmark_local_job(request, params, db)


@router.delete("/{local_job_id}/bookmark")
async def unbookmark_local_job(
    request: Request,
    params:  LocalJobIdSchema = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await local_job_controller.unbookmark_local_job(request, params, db)