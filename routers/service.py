from database import get_db
from .middleware.auth_middleware import authenticate_token

from fastapi import APIRouter, Depends, Query, Request, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from schemas.service_schemas import (
    GuestGetServicesSchema,

    GetServicesSchema,
    PublishServiceStateOptionsSchema,
    ServiceIdSchema,
    GetUserProfileServicesSchema,
    GetServicesByUserIdSchema,

    CreateServiceSchema,
    GetPublishedServicesSchema,

    UpdateServiceInfoSchema,
    UpdateServiceThumbnailSchema,
    UpdateServiceImagesSchema,
    UpdateServicePlansSchema,

    ServiceSearchSuggestionsSchema,
    UpdateIndustriesSchema,
    create_guest_get_services_params,

    create_service_form,
    update_thumbnail_form,
    update_service_images_form,
)

from controllers import service_controller

router = APIRouter(
    prefix="/services",
    tags=["Services"],
)

#Guest
@router.get("/guest")
async def guest_get_services(
    request: Request,
    schema:  GuestGetServicesSchema = Depends(create_guest_get_services_params),
    db:      AsyncSession = Depends(get_db),
):
    return await service_controller.guest_get_services(request, schema, db)

@router.get("/guest/industries")
async def guest_get_industries(
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    return await service_controller.get_industries(request, db)

@router.get("/guest/{service_id}")
async def guest_get_service_by_service_id(
    request: Request,
    schema:  ServiceIdSchema = Depends(),
    db:      AsyncSession = Depends(get_db),
):
    return await service_controller.get_service_by_service_id(request, schema, db)

@router.get("/guest/users/profile/{user_id}")
async def guest_get_user_profile_and_services_by_user_id(
    request: Request,
    schema:   GetUserProfileServicesSchema = Depends(),
    db:      AsyncSession = Depends(get_db),
):
    return await service_controller.get_user_profile_and_services_by_user_id(request, schema, db)

@router.get("/guest/users/{user_id}")
async def guest_get_services_by_user_id(
    request: Request,
    schema:   GetServicesByUserIdSchema = Depends(),
    db:      AsyncSession = Depends(get_db),
):
    return await service_controller.get_services_by_user_id(request, schema, db)

@router.get("/guest/search-suggestions")
async def guest_search_suggestions(
    request: Request,
    schema:  ServiceSearchSuggestionsSchema = Depends(),
    db:      AsyncSession = Depends(get_db),
):
    return await service_controller.services_search_suggestions(request, schema, db)

#User
@router.get("")
async def get_services(
    request: Request,
    schema:  GetServicesSchema = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await service_controller.get_services(request, schema, db)

@router.get("/users/profile/{user_id}")
async def get_user_profile_and_services_by_user_id(
    request: Request,
    schema:   GetUserProfileServicesSchema = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await service_controller.get_user_profile_and_services_by_user_id(request, schema, db)

@router.get("/users/{user_id}")
async def get_services_by_user_id(
    request: Request,
    schema:   GetServicesByUserIdSchema = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await service_controller.get_services_by_user_id(request, schema, db)

@router.post("/create-service")
async def create_service(
    request:   Request,
    schema:      CreateServiceSchema = Depends(create_service_form),
    db:        AsyncSession = Depends(get_db),
    _:         None = Depends(authenticate_token),
):
    return await service_controller.create_service(request, schema, db)


@router.get("/published")
async def get_published_services(
    request: Request,
    schema:  GetPublishedServicesSchema = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await service_controller.get_published_services(request, schema, db)

@router.get("/published/{service_id}/info")
async def get_published_service_info(
    request: Request,
    schema:  ServiceIdSchema = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await service_controller.get_published_service_info(request, schema, db)

@router.get("/published/{service_id}/thumbnail")
async def get_published_service_thumbnail(
    request: Request,
    schema:  ServiceIdSchema = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await service_controller.get_published_service_thumbnail(request, schema, db)

@router.get("/published/{service_id}/images")
async def get_published_service_images(
    request: Request,
    schema:  ServiceIdSchema = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await service_controller.get_published_service_images(request, schema, db)

@router.get("/published/{service_id}/plans")
async def get_published_service_plans(
    request: Request,
    schema:  ServiceIdSchema = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await service_controller.get_published_service_plans(request, schema, db)

@router.patch("/published/{service_id}/info")
async def update_service_info(
    request: Request,
    schema: UpdateServiceInfoSchema,
    params: ServiceIdSchema = Depends(),
    db:        AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
): 
    schema.service_id = params.service_id
    return await service_controller.update_service_info(request, schema, db)

@router.patch("/published/{service_id}/thumbnail")
async def update_service_thumbnail(
    request:   Request,
    schema:      UpdateServiceThumbnailSchema = Depends(update_thumbnail_form),
    db:        AsyncSession = Depends(get_db),
    _:         None = Depends(authenticate_token),
):
    return await service_controller.update_service_thumbnail(request, schema, db)

@router.patch("/published/{service_id}/service-images")
async def update_service_images(
    request: Request,
    schema:    UpdateServiceImagesSchema = Depends(update_service_images_form),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await service_controller.update_service_images(request, schema, db)

@router.patch("/published/{service_id}/plans")
async def update_service_plans(
    request: Request,
    schema:  UpdateServicePlansSchema,
    params: ServiceIdSchema = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    schema.service_id = params.service_id
    return await service_controller.update_service_plans(request, schema, db)

@router.get("/search-suggestions")
async def search_suggestions(
    request: Request,
    schema:  ServiceSearchSuggestionsSchema = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await service_controller.services_search_suggestions(request, schema, db)

@router.get("/industries")
async def get_industries(
    request: Request,
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await service_controller.get_user_industries(request, db)

@router.put("/industries")
async def update_industries(
    schema:    UpdateIndustriesSchema,
    request: Request,
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await service_controller.update_industries(request, schema, db)

@router.get("/publish/meta/options")
async def get_publish_countries_options(
    request: Request,
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await service_controller.get_publish_meta_options(request, db)

@router.get("/publish/meta/options/info")
async def get_publish_countries_options(
    request: Request,
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await service_controller.get_publish_meta_options(request, db)

@router.get("/publish/meta/options/plans")
async def get_publish_countries_options(
    request: Request,
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await service_controller.get_publish_meta_options(request, db)


@router.get("/publish/location/states/options")
async def get_publish_states_options(
    request: Request,
    schema:  PublishServiceStateOptionsSchema = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await service_controller.get_publish_states_options(request, schema, db)

@router.get("/{service_id}")
async def get_service_by_service_id(
    request: Request,
    schema:  ServiceIdSchema = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await service_controller.get_service_by_service_id(request, schema, db)

@router.delete("/{service_id}")
async def delete_service(
    request: Request,
    schema:  ServiceIdSchema = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await service_controller.delete_service(request, schema, db)

@router.post("/{service_id}/bookmark")
async def bookmark_service(
    request: Request,
    schema:  ServiceIdSchema = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await service_controller.bookmark_service(request, schema, db)

@router.delete("/{service_id}/bookmark")
async def unbookmark_service(
    request: Request,
    schema:  ServiceIdSchema = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await service_controller.unbookmark_service(request, schema, db)

