from database import get_db
from .middleware.auth_middleware import authenticate_token

from fastapi import APIRouter, Depends, Request, Path, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from schemas.used_product_listing_schemas import (
    GuestGetUsedProductListingsSchema,

    GetUsedProductListingsSchema,
    UsedProductListingIdParam,
    GetUserProfileUsedProductListingsSchema,
    GetUsedProductListingsByUserIdSchema,
    GetPublishedUsedProductListingsSchema,
    CreateOrUpdateUsedProductListingSchema,
    create_or_update_used_product_listing_form,

    UsedProductListingsSearchSuggestionsSchema
)

from controllers import used_product_listing_controller

router = APIRouter(
    prefix="/used-product-listings",
    tags=["Used Product Listings"],
)

@router.get("/guest")
async def guest_get_used_product_listings(
    request: Request,
    schema:  GuestGetUsedProductListingsSchema = Depends(),
    db:      AsyncSession = Depends(get_db),
):
    return await used_product_listing_controller.guest_get_used_product_listings(request, schema, db)

@router.get("/guest/users/profile/{user_id}")
async def guest_get_user_profile_and_used_product_listings_by_user_id(
    request: Request,
    schema:   GetUserProfileUsedProductListingsSchema = Depends(),
    db:      AsyncSession = Depends(get_db),
):
    return await used_product_listing_controller.get_user_profile_and_used_product_listings(request, schema, db)


@router.get("/guest/users/{user_id}")
async def guest_get_used_product_listings_by_user_id(
    request: Request,
    schema:   GetUsedProductListingsByUserIdSchema = Depends(),
    db:      AsyncSession = Depends(get_db),
):
    return await used_product_listing_controller.get_used(request, schema, db)


@router.get("/guest/{used_product_listing_id}")
async def guest_get_used_product_listing_by_id(
    request: Request,
    schema:  UsedProductListingIdParam = Depends(),
    db:      AsyncSession = Depends(get_db),
):
    return await used_product_listing_controller.get_used_product_listing_by_used_product_listing_id(request, schema, db)

@router.get("/guest/search-suggestions")
async def guest_used_product_listings_search_suggestions(
    request: Request,
    schema:  UsedProductListingsSearchSuggestionsSchema = Depends(),
    db:      AsyncSession = Depends(get_db),
):
    return await used_product_listing_controller.used_product_listings_search_suggestions(request, schema, db)

@router.get("/users/profile/{user_id}")
async def get_user_profile_and_used_product_listings_by_user_id(
    request: Request,
    schema:   GetUserProfileUsedProductListingsSchema = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await used_product_listing_controller.get_user_profile_and_used_product_listings(request, schema, db)


@router.get("/users/{user_id}")
async def get_used_product_listings_by_user_id(
    request: Request,
    schema:   GetUsedProductListingsByUserIdSchema = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await used_product_listing_controller.get_used_product_listings_by_user_id(request, schema, db)

@router.get("")
async def get_used_product_listings(
    request: Request,
    schema:  GetUsedProductListingsSchema = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await used_product_listing_controller.get_used_product_listings(request, schema, db)

@router.post("")
async def create_or_update_used_product_listing(
    request: Request,
    schema:    CreateOrUpdateUsedProductListingSchema = Depends(create_or_update_used_product_listing_form),
    images:  Optional[List[UploadFile]] = File(default=None),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await used_product_listing_controller.create_or_update_used_product_listing(request, schema, db)

@router.get("/published")
async def get_published_used_product_listings(
    request: Request,
    schema:  GetPublishedUsedProductListingsSchema = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await used_product_listing_controller.get_published_used_product_listings(request, schema, db)

@router.get("/{used_product_listing_id}")
async def get_used_product_listing_by_used_product_listing_id(
    request: Request,
    schema:  UsedProductListingIdParam = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await used_product_listing_controller.get_used_product_listing_by_used_product_listing_id(request, schema, db)


@router.post("/{used_product_listing_id}/bookmark")
async def bookmark_used_product_listing(
    request: Request,
    schema:  UsedProductListingIdParam = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await used_product_listing_controller.bookmark_used_product_listing(request, schema, db)


@router.delete("/{used_product_listing_id}/bookmark")
async def unbookmark_used_product_listing(
    request: Request,
    schema:  UsedProductListingIdParam = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await used_product_listing_controller.unbookmark_used_product_listing(request, schema, db)

@router.delete("/{used_product_listing_id}")
async def delete_used_product_listing(
    request: Request,
    schema:  UsedProductListingIdParam = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await used_product_listing_controller.delete_used_product_listing(request, schema, db)

@router.get("/search-suggestions")
async def used_product_listings_search_suggestions(
    request: Request,
    schema:  UsedProductListingsSearchSuggestionsSchema = Depends(),
    db:      AsyncSession = Depends(get_db),
    _:       None = Depends(authenticate_token),
):
    return await used_product_listing_controller.used_product_listings_search_suggestions(request, schema, db)
