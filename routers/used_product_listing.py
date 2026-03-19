from database import get_db
from .middleware.auth_middleware import authenticate_token

from fastapi import APIRouter, Depends, Request, Path, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from schemas.used_product_listing_schemas import (
    GuestGetUsedProductListingsRequest,
    GetUsedProductListingsRequest,
    GetUsedProductListingsByUserIdRequest,
    GetUserProfileRequest,
    GetMeUsedProductListingsRequest,
    UsedProductSearchSuggestionsRequest,
    UsedProductListingIdParam,
    UserIdParam,
    CreateOrUpdateUsedProductListingRequest,
    create_or_update_used_product_listing_form,
)

from controllers import used_product_listing_controller

router = APIRouter(
    prefix="/used-products",
    tags=["Used Products"],
)


@router.get("/guest/search-suggestions")
async def guest_used_product_listings_search_suggestions(
    request: Request,
    params:  UsedProductSearchSuggestionsRequest = Depends(),
    db:      AsyncSession = Depends(get_db),
):
    return await used_product_listing_controller.used_product_listings_search_queries(request, params, db)


@router.get("/guest/users/profile/{user_id}")
async def guest_get_user_profile_and_used_product_listings_by_user_id(
    request: Request,
    params:  UserIdParam = Depends(),
    query:   GetUserProfileRequest = Depends(),
    db:      AsyncSession = Depends(get_db),
):
    return await used_product_listing_controller.guest_get_user_profile_and_used_product_listings_by_user_id(request, params.user_id, query, db)


@router.get("/guest/users/{user_id}")
async def guest_get_used_product_listings_by_user_id(
    request: Request,
    params:  UserIdParam = Depends(),
    query:   GetUsedProductListingsByUserIdRequest = Depends(),
    db:      AsyncSession = Depends(get_db),
):
    return await used_product_listing_controller.guest_get_used_product_listings_by_user_id(request, params.user_id, query, db)


@router.get("/guest/{used_product_listing_id}")
async def guest_get_used_product_listing_by_id(
    request: Request,
    params:  UsedProductListingIdParam = Depends(),
    db:      AsyncSession = Depends(get_db),
):
    return await used_product_listing_controller.guest_get_used_product_listing_by_used_product_listing_id(request, params.used_product_listing_id, db)


@router.get("/guest")
async def guest_get_used_product_listings(
    request: Request,
    params:  GuestGetUsedProductListingsRequest = Depends(),
    db:      AsyncSession = Depends(get_db),
):
    return await used_product_listing_controller.guest_get_used_product_listings(request, params, db)


@router.get("/search-suggestions")
async def used_product_listings_search_suggestions(
    request: Request,
    params:  UsedProductSearchSuggestionsRequest = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await used_product_listing_controller.used_product_listings_search_queries(request, params, db)


@router.get("/me")
async def get_me_used_product_listings(
    request: Request,
    params:  GetMeUsedProductListingsRequest = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await used_product_listing_controller.get_me_used_product_listings(request, params, db)


@router.get("/users/profile/{user_id}")
async def get_user_profile_and_used_product_listings_by_user_id(
    request: Request,
    params:  UserIdParam = Depends(),
    query:   GetUserProfileRequest = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await used_product_listing_controller.get_user_profile_and_used_product_listings_by_user_id(request, params.user_id, query, db)


@router.get("/users/{user_id}")
async def get_used_product_listings_by_user_id(
    request: Request,
    params:  UserIdParam = Depends(),
    query:   GetUsedProductListingsByUserIdRequest = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await used_product_listing_controller.get_used_product_listings_by_user_id(request, params.user_id, query, db)


@router.get("/{used_product_listing_id}")
async def get_used_product_listing_by_id(
    request: Request,
    params:  UsedProductListingIdParam = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await used_product_listing_controller.get_used_product_listing_by_used_product_listing_id(request, params.used_product_listing_id, db)


@router.get("/")
async def get_used_product_listings(
    request: Request,
    params:  GetUsedProductListingsRequest = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await used_product_listing_controller.get_used_product_listings(request, params, db)


@router.post("/")
async def create_or_update_used_product_listing(
    request: Request,
    body:    CreateOrUpdateUsedProductListingRequest = Depends(create_or_update_used_product_listing_form),
    images:  Optional[List[UploadFile]] = File(default=None),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    has_new_images  = images and len(images) > 0
    has_kept_images = body.keep_image_ids and len(body.keep_image_ids) > 0
    if not has_new_images and not has_kept_images:
        raise HTTPException(status_code=422, detail="At least one image is required")

    return await used_product_listing_controller.create_or_update_used_product_listing(request, body, images, db)


@router.delete("/{used_product_listing_id}")
async def delete_used_product_listing(
    request: Request,
    params:  UsedProductListingIdParam = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await used_product_listing_controller.delete_used_product_listing(request, params.used_product_listing_id, db)


@router.post("/{used_product_listing_id}/bookmark")
async def bookmark_used_product_listing(
    request: Request,
    params:  UsedProductListingIdParam = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await used_product_listing_controller.bookmark_used_product_listing(request, params.used_product_listing_id, db)


@router.delete("/{used_product_listing_id}/bookmark")
async def unbookmark_used_product_listing(
    request: Request,
    params:  UsedProductListingIdParam = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await used_product_listing_controller.unbookmark_used_product_listing(request, params.used_product_listing_id, db)