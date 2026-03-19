from fastapi import APIRouter, Depends, Request, Query
from typing import Optional
from middleware.auth_middleware import authenticate_token
from schemas.app_schemas import (
    UpdateFCMTokenRequest,
    UpdateE2EEPublicKeyRequest,
    SyncContactsRequest,
)

router = APIRouter(
    prefix="/app",
    tags=["App"],
    dependencies=[Depends(authenticate_token)],
)


@router.put("/fcm-token")
async def update_fcm_token(body: UpdateFCMTokenRequest, request: Request):
    pass


@router.put("/ee2ee-public-key")
async def update_e2ee_public_key(body: UpdateE2EEPublicKeyRequest, request: Request):
    pass


@router.get("/bookmarks")
async def get_bookmarks(
    request:        Request,
    page_size:      Optional[int] = Query(default=None),
    next_token:     Optional[str] = Query(default=None),
    previous_token: Optional[str] = Query(default=None),
):
    pass


@router.post("/sync-contacts")
async def sync_contacts(body: SyncContactsRequest, request: Request):
    pass


@router.get("/search-chats")
async def search_chats(
    request: Request,
    search:  str = Query(..., min_length=1),
):
    pass


@router.get("/lookup/phone")
async def search_by_number(
    request:      Request,
    country_code: str = Query(..., min_length=1),
    local_number: str = Query(..., min_length=1),
):
    pass