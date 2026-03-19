# routers/services.py
from fastapi import APIRouter, Depends, Request, Query, UploadFile, File
from typing import Optional, List
from middleware.auth_middleware import authenticate_token
from schemas.service_schemas import (
    CreateServiceRequest,
    UpdateServiceInfoRequest,
    UpdateServicePlansRequest,
    UpdateServiceImagesRequest,
    UpdateServiceLocationRequest,
    UpdateIndustriesRequest,
)

router = APIRouter(
    prefix="/services",
    tags=["Services"],
)


# ── Guest routes ──────────────────────────────────────────────────────────────

@router.get("/guest")
async def guest_get_services(
    request:        Request,
    s:              Optional[str]   = Query(default=None, max_length=100),
    latitude:       Optional[float] = Query(default=None, ge=-90,  le=90),
    longitude:      Optional[float] = Query(default=None, ge=-180, le=180),
    industries:     Optional[List[int]] = Query(default=None),
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


@router.get("/guest/industries")
async def guest_get_industries(request: Request):
    pass


@router.get("/guest/users/profile/{user_id}")
async def guest_get_user_profile_and_services(
    user_id:   int,
    request:   Request,
    page_size: Optional[int] = Query(default=None),
):
    pass


@router.get("/guest/users/{user_id}")
async def guest_get_services_by_user_id(
    user_id:        int,
    request:        Request,
    page_size:      Optional[int] = Query(default=None),
    next_token:     Optional[str] = Query(default=None),
    previous_token: Optional[str] = Query(default=None),
):
    pass


@router.get("/guest/{service_id}")
async def guest_get_service_by_service_id(
    service_id: int,
    request:    Request,
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


@router.get("/industries")
async def get_industries(
    request:      Request,
    current_user=Depends(authenticate_token),
):
    pass


@router.put("/industries")
async def update_industries(
    body:         UpdateIndustriesRequest,
    request:      Request,
    current_user=Depends(authenticate_token),
):
    pass


@router.get("/me")
async def get_me_services(
    request:        Request,
    page_size:      Optional[int] = Query(default=None),
    next_token:     Optional[str] = Query(default=None),
    previous_token: Optional[str] = Query(default=None),
    current_user=Depends(authenticate_token),
):
    pass


@router.get("/")
async def get_services(
    request:        Request,
    s:              Optional[str] = Query(default=None, max_length=100),
    page_size:      Optional[int] = Query(default=None),
    next_token:     Optional[str] = Query(default=None),
    previous_token: Optional[str] = Query(default=None),
    current_user=Depends(authenticate_token),
):
    pass


@router.get("/users/profile/{user_id}")
async def get_user_profile_and_services(
    user_id:      int,
    request:      Request,
    page_size:    Optional[int] = Query(default=None),
    current_user=Depends(authenticate_token),
):
    pass


@router.get("/users/{user_id}")
async def get_services_by_user_id(
    user_id:        int,
    request:        Request,
    page_size:      Optional[int] = Query(default=None),
    next_token:     Optional[str] = Query(default=None),
    previous_token: Optional[str] = Query(default=None),
    current_user=Depends(authenticate_token),
):
    pass


@router.get("/{service_id}")
async def get_service_by_service_id(
    service_id:   int,
    request:      Request,
    current_user=Depends(authenticate_token),
):
    pass


@router.post("/create-service")
async def create_service(
    request:      Request,
    body:         CreateServiceRequest,
    thumbnail:    UploadFile = File(...),
    images:       List[UploadFile] = File(...),
    current_user=Depends(authenticate_token),
):
    pass


@router.patch("/{service_id}/info")
async def update_service_info(
    service_id:   int,
    body:         UpdateServiceInfoRequest,
    request:      Request,
    current_user=Depends(authenticate_token),
):
    pass


@router.patch("/{service_id}/thumbnail")
async def update_service_thumbnail(
    service_id:   int,
    request:      Request,
    thumbnail:    UploadFile = File(...),
    current_user=Depends(authenticate_token),
):
    pass


@router.patch("/{service_id}/update-service-images")
async def update_service_images(
    service_id:   int,
    request:      Request,
    body:         UpdateServiceImagesRequest,
    images:       Optional[List[UploadFile]] = File(default=None),
    current_user=Depends(authenticate_token),
):
    pass


@router.patch("/{service_id}/plans")
async def update_service_plans(
    service_id:   int,
    body:         UpdateServicePlansRequest,
    request:      Request,
    current_user=Depends(authenticate_token),
):
    pass


@router.patch("/{service_id}/location")
async def update_service_location(
    service_id:   int,
    body:         UpdateServiceLocationRequest,
    request:      Request,
    current_user=Depends(authenticate_token),
):
    pass


@router.delete("/{service_id}")
async def delete_service(
    service_id:   int,
    request:      Request,
    current_user=Depends(authenticate_token),
):
    pass


@router.post("/{service_id}/bookmark")
async def bookmark_service(
    service_id:   int,
    request:      Request,
    current_user=Depends(authenticate_token),
):
    pass


@router.delete("/{service_id}/bookmark")
async def unbookmark_service(
    service_id:   int,
    request:      Request,
    current_user=Depends(authenticate_token),
):
    pass