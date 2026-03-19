from database import get_db
from .middleware.auth_middleware import authenticate_token

from fastapi import APIRouter, Depends, Request, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from schemas.service_schemas import (
    GuestGetServicesRequest,
    GetServicesRequest,
    GetMeServicesRequest,
    GetUserProfileServicesRequest,
    GetServicesByUserIdRequest,
    SearchSuggestionsRequest,
    ServiceIdParam,
    UserIdParam,
    CreateServiceRequest,
    create_service_form,
    UpdateServiceInfoRequest,
    UpdateServiceThumbnailRequest,
    UpdateServiceImagesRequest,
    update_service_images_form,
    UpdateServicePlansRequest,
    UpdateServiceLocationRequest,
    UpdateIndustriesRequest,
)

from controllers import service_controller

router = APIRouter(
    prefix="/services",
    tags=["Services"],
)


# ──────────────────────────────────────────────
# Static guest routes  (must come before /{service_id})
# ──────────────────────────────────────────────

@router.get("/guest/search-suggestions")
async def guest_search_suggestions(
    request: Request,
    params:  SearchSuggestionsRequest = Depends(),
    db:      AsyncSession = Depends(get_db),
):
    return await service_controller.search_suggestions(request, params, db)


@router.get("/guest/industries")
async def guest_get_industries(
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    return await service_controller.guest_get_industries(request, db)


@router.get("/guest/users/profile/{user_id}")
async def guest_get_user_profile_and_services_by_user_id(
    request: Request,
    params:  UserIdParam = Depends(),
    query:   GetUserProfileServicesRequest = Depends(),
    db:      AsyncSession = Depends(get_db),
):
    return await service_controller.guest_get_user_profile_and_services_by_user_id(request, params.user_id, query, db)


@router.get("/guest/users/{user_id}")
async def guest_get_services_by_user_id(
    request: Request,
    params:  UserIdParam = Depends(),
    query:   GetServicesByUserIdRequest = Depends(),
    db:      AsyncSession = Depends(get_db),
):
    return await service_controller.guest_get_services_by_user_id(request, params.user_id, query, db)


@router.get("/guest/{service_id}")
async def guest_get_service_by_service_id(
    request: Request,
    params:  ServiceIdParam = Depends(),
    db:      AsyncSession = Depends(get_db),
):
    return await service_controller.guest_get_service_by_service_id(request, params.service_id, db)


@router.get("/guest")
async def guest_get_services(
    request: Request,
    params:  GuestGetServicesRequest = Depends(),
    db:      AsyncSession = Depends(get_db),
):
    return await service_controller.guest_get_services(request, params, db)


# ──────────────────────────────────────────────
# Static authenticated routes (must come before /{service_id})
# ──────────────────────────────────────────────

@router.get("/search-suggestions")
async def search_suggestions(
    request: Request,
    params:  SearchSuggestionsRequest = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await service_controller.search_suggestions(request, params, db)


@router.get("/industries")
async def get_industries(
    request: Request,
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await service_controller.get_industries(request, db)


@router.put("/industries")
async def update_industries(
    body:    UpdateIndustriesRequest,
    request: Request,
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await service_controller.update_industries(request, body, db)


@router.get("/me")
async def get_me_services(
    request: Request,
    params:  GetMeServicesRequest = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await service_controller.get_me_services(request, params, db)


@router.post("/create-service")
async def create_service(
    request:   Request,
    body:      CreateServiceRequest = Depends(create_service_form),
    thumbnail: UploadFile            = File(...),
    images:    Optional[List[UploadFile]] = File(default=None),
    db:        AsyncSession = Depends(get_db),
    _:         None = Depends(authenticate_token),
):
    if not thumbnail:
        raise HTTPException(status_code=422, detail="Thumbnail image is required")
    if not images or len(images) == 0:
        raise HTTPException(status_code=422, detail="At least one image is required")

    return await service_controller.create_service(request, body, thumbnail, images, db)


@router.get("/users/profile/{user_id}")
async def get_user_profile_and_services_by_user_id(
    request: Request,
    params:  UserIdParam = Depends(),
    query:   GetUserProfileServicesRequest = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await service_controller.get_user_profile_and_services_by_user_id(request, params.user_id, query, db)


@router.get("/users/{user_id}")
async def get_services_by_user_id(
    request: Request,
    params:  UserIdParam = Depends(),
    query:   GetServicesByUserIdRequest = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await service_controller.get_services_by_user_id(request, params.user_id, query, db)


@router.get("/")
async def get_services(
    request: Request,
    params:  GetServicesRequest = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await service_controller.get_services(request, params, db)


# ──────────────────────────────────────────────
# Dynamic routes /{service_id}
# ──────────────────────────────────────────────

@router.get("/{service_id}")
async def get_service_by_service_id(
    request: Request,
    params:  ServiceIdParam = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await service_controller.get_service_by_service_id(request, params.service_id, db)


@router.patch("/{service_id}/info")
async def update_service_info(
    body:    UpdateServiceInfoRequest,
    request: Request,
    params:  ServiceIdParam = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await service_controller.update_service_info(request, params.service_id, body, db)


@router.patch("/{service_id}/thumbnail")
async def update_service_thumbnail(
    request:   Request,
    params:    ServiceIdParam = Depends(),
    body:      UpdateServiceThumbnailRequest = Depends(),
    thumbnail: UploadFile = File(...),
    db:        AsyncSession = Depends(get_db),
    _:         None = Depends(authenticate_token),
):
    if not thumbnail:
        raise HTTPException(status_code=422, detail="Thumbnail image is required")

    return await service_controller.update_service_thumbnail(request, params.service_id, body, thumbnail, db)


@router.patch("/{service_id}/update-service-images")
async def update_service_images(
    request: Request,
    params:  ServiceIdParam = Depends(),
    body:    UpdateServiceImagesRequest = Depends(update_service_images_form),
    images:  Optional[List[UploadFile]] = File(default=None),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    has_new_images  = images and len(images) > 0
    has_kept_images = body.keep_image_ids and len(body.keep_image_ids) > 0
    if not has_new_images and not has_kept_images:
        raise HTTPException(status_code=422, detail="At least 1 image is required")

    return await service_controller.update_service_images(request, params.service_id, body, images, db)


@router.patch("/{service_id}/plans")
async def update_service_plans(
    body:    UpdateServicePlansRequest,
    request: Request,
    params:  ServiceIdParam = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await service_controller.update_service_plans(request, params.service_id, body, db)


@router.patch("/{service_id}/location")
async def update_service_location(
    body:    UpdateServiceLocationRequest,
    request: Request,
    params:  ServiceIdParam = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await service_controller.update_service_location(request, params.service_id, body, db)


@router.delete("/{service_id}")
async def delete_service(
    request: Request,
    params:  ServiceIdParam = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await service_controller.delete_service(request, params.service_id, db)


@router.post("/{service_id}/bookmark")
async def bookmark_service(
    request: Request,
    params:  ServiceIdParam = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await service_controller.bookmark_service(request, params.service_id, db)


@router.delete("/{service_id}/bookmark")
async def unbookmark_service(
    request: Request,
    params:  ServiceIdParam = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await service_controller.unbookmark_service(request, params.service_id, db)