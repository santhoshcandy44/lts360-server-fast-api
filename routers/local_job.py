from database import get_db
from .middleware.auth_middleware import authenticate_token

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from schemas.local_job_schemas import (
    CreateLocalJobSchema,
    GuestGetLocalJobsSchema,

    GetLocalJobsbSchema, 
    LocalJobIdSchema,
    
    GetPublishedLocalJobsSchema,
    GetLocalJobApplicationsSchema,
    LocalJobApplicationSchema,
    PublishLocalJobStateOptionsSchema,
    
    SearchSuggestionsSchema,
    UpdateLocalJobSchema,
    create_local_job_form,
    update_local_job_form
)

from controllers import local_job_controller

router = APIRouter(
    prefix="/local-jobs",
    tags=["Local Jobs"],
)

@router.get("/guest")
async def guest_get_local_jobs(
    request: Request,
    schema:  GuestGetLocalJobsSchema = Depends(),
    db:      AsyncSession = Depends(get_db),
):
    return await local_job_controller.guest_get_local_jobs(request, schema, db)

@router.get("/guest/{local_job_id}")
async def guest_get_local_job(
    request:      Request,
    schema:       LocalJobIdSchema = Depends(),
    db:           AsyncSession = Depends(get_db),
):
    return await local_job_controller.get_local_jobs(request, schema, db)

@router.get("/guest/search-suggestions")
async def guest_local_jobs_search_suggestion(
    request: Request,
    schema:  SearchSuggestionsSchema = Depends(),
    db:      AsyncSession = Depends(get_db),
):
    return await local_job_controller.local_jobs_search_suggestion(request, schema, db)


@router.get("")
async def get_local_jobs(
    request: Request,
    schema:  GetLocalJobsbSchema = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await local_job_controller.get_local_jobs(request, schema, db)

@router.post("")
async def create_local_job(
    request: Request,
    schema:  CreateLocalJobSchema = Depends(create_local_job_form),
    db:      AsyncSession                 = Depends(get_db),
    _:       None                         = Depends(authenticate_token),
):
    return await local_job_controller.create_local_job(request, schema, db)

@router.put("/{local_job_id}")
async def update_local_job(
    request: Request,
    schema:    UpdateLocalJobSchema = Depends(update_local_job_form),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await local_job_controller.update_local_job(request, schema, db)  

@router.get("/published")                               
async def get_publishd_local_jobs(
    request: Request,
    schema:  GetPublishedLocalJobsSchema = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await local_job_controller.get_published_local_jobs(request, schema, db)

@router.get("/publish/location/countries/options")
async def get_publish_countries_options(
    request: Request,
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await local_job_controller.get_publish_countries_options(request, db)


@router.get("/publish/location/states/options")
async def get_publish_states_options(
    request: Request,
    schema:  PublishLocalJobStateOptionsSchema = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await local_job_controller.get_publish_states_options(request, schema, db)

@router.get("/{local_job_id}")                   
async def get_local_job(
    request:      Request,
    schema:       LocalJobIdSchema = Depends(),
    db:           AsyncSession = Depends(get_db),
    _:            None = Depends(authenticate_token),
):
    return await local_job_controller.get_local_job(request, schema, db)

@router.post("/{local_job_id}/apply")
async def apply_local_job(
    request: Request,
    schema:  LocalJobIdSchema = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await local_job_controller.apply_local_job(request, schema, db)

@router.delete("/{local_job_id}")
async def delete_local_job(
    request: Request,
    schema:  LocalJobIdSchema = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await local_job_controller.delete_local_job(request, schema, db)


@router.get("/{local_job_id}/applications")
async def get_local_job_applications(
    request: Request,
    schema:  GetLocalJobApplicationsSchema = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await local_job_controller.get_local_job_applications(request, schema, db)

@router.post("/{local_job_id}/applications/{application_id}/review")
async def mark_as_reviewed_local_job(
    request: Request,
    schema:  LocalJobApplicationSchema= Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await local_job_controller.mark_as_reviewed_local_job_application(request, schema, db)

@router.delete("/{local_job_id}/applications/{application_id}/review")
async def unmark_reviewed_local_job(
    request: Request,
    schema:  LocalJobApplicationSchema = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await local_job_controller.unmark_reviewed_local_job_application(request, schema, db)

@router.post("/{local_job_id}/bookmark")
async def bookmark_local_job(
    request: Request,
    schema:  LocalJobIdSchema = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await local_job_controller.bookmark_local_job(request, schema, db)


@router.delete("/{local_job_id}/bookmark")
async def unbookmark_local_job(
    request: Request,
    schema:  LocalJobIdSchema = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await local_job_controller.unbookmark_local_job(request, schema, db)

@router.get("/search-suggestions")
async def local_jobs_search_suggestion(
    request: Request,
    schema:  SearchSuggestionsSchema = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await local_job_controller.local_jobs_search_queries(request, schema, db)
