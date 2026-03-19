from fastapi import APIRouter, Depends, Request, Query, UploadFile, File
from typing import Optional, List
from middleware.auth_middleware import authenticate_token
from schemas.used_product_schemas import CreateUsedProductListingRequest

router = APIRouter(
    prefix="/used-product-listings",
    tags=["Used Products"],
)

@router.get("/guest")
async def guest_get_used_product_listings(
    request:        Request,
    s:              Optional[str]   = Query(default=None, max_length=100),
    latitude:       Optional[float] = Query(default=None, ge=-90,  le=90),
    longitude:      Optional[float] = Query(default=None, ge=-180, le=180),
    page_size:      Optional[int]   = Query(default=None),
    next_token:     Optional[str]   = Query(default=None),
    previous_token: Optional[str]   = Query(default=None),
):
    pass


@router.get("/guest/search-suggestions")
async def guest_search_suggestions(
    request: Request,
    query:   str = Query(..., min_length=1),
):
    pass


@router.get("/guest/users/profile/{user_id}")
async def guest_get_user_profile_and_listings(
    user_id:   int,
    request:   Request,
    page_size: Optional[int] = Query(default=None),
):
    pass


@router.get("/guest/users/{user_id}")
async def guest_get_listings_by_user_id(
    user_id:        int,
    request:        Request,
    page_size:      Optional[int] = Query(default=None),
    next_token:     Optional[str] = Query(default=None),
    previous_token: Optional[str] = Query(default=None),
):
    pass


@router.get("/guest/{used_product_listing_id}")
async def guest_get_listing_by_id(
    used_product_listing_id: int,
    request:                 Request,
):
    pass


# ── Protected routes ──────────────────────────────────────────────────────────

@router.get("/search-suggestions")
async def search_suggestions(
    request:      Request,
    query:        str = Query(..., min_length=1),
    current_user=Depends(authenticate_token),
):
    pass


@router.get("/me")
async def get_me_listings(
    request:        Request,
    page_size:      Optional[int] = Query(default=None),
    next_token:     Optional[str] = Query(default=None),
    previous_token: Optional[str] = Query(default=None),
    current_user=Depends(authenticate_token),
):
    pass


@router.get("/")
async def get_used_product_listings(
    request:        Request,
    s:              Optional[str] = Query(default=None, max_length=100),
    page_size:      Optional[int] = Query(default=None),
    next_token:     Optional[str] = Query(default=None),
    previous_token: Optional[str] = Query(default=None),
    current_user=Depends(authenticate_token),
):
    pass


@router.get("/users/profile/{user_id}")
async def get_user_profile_and_listings(
    user_id:      int,
    request:      Request,
    page_size:    Optional[int] = Query(default=None),
    current_user=Depends(authenticate_token),
):
    pass


@router.get("/users/{user_id}")
async def get_listings_by_user_id(
    user_id:        int,
    request:        Request,
    page_size:      Optional[int] = Query(default=None),
    next_token:     Optional[str] = Query(default=None),
    previous_token: Optional[str] = Query(default=None),
    current_user=Depends(authenticate_token),
):
    pass


@router.get("/{used_product_listing_id}")
async def get_listing_by_id(
    used_product_listing_id: int,
    request:                 Request,
    current_user=Depends(authenticate_token),
):
    pass


@router.post("/")
async def create_or_update_listing(
    request:      Request,
    body:         CreateUsedProductListingRequest,
    images:       Optional[List[UploadFile]] = File(default=None),
    current_user=Depends(authenticate_token),
):
    pass


@router.delete("/{used_product_listing_id}")
async def delete_listing(
    used_product_listing_id: int,
    request:                 Request,
    current_user=Depends(authenticate_token),
):
    pass


@router.post("/{used_product_listing_id}/bookmark")
async def bookmark_listing(
    used_product_listing_id: int,
    request:                 Request,
    current_user=Depends(authenticate_token),
):
    pass


@router.delete("/{used_product_listing_id}/bookmark")
async def unbookmark_listing(
    used_product_listing_id: int,
    request:                 Request,
    current_user=Depends(authenticate_token),
):
    pass