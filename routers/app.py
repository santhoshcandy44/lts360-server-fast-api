from database import get_db
from .middleware.auth_middleware import authenticate_token

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from schemas.app_schemas import (
    UpdateFCMTokenRequest,
    UpdateE2EEPublicKeyRequest,
    SyncContactsRequest,
    GetBookmarksSchema,
    SearchChatsRequest,
    LookupByPhoneRequest,
)

from controllers import app_controller

router = APIRouter(
    prefix="/app",
    tags=["App"],
    dependencies=[Depends(authenticate_token)],
)


@router.put("/fcm-token")
async def update_fcm_token(
    body:    UpdateFCMTokenRequest,
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    return await app_controller.update_fcm_token(request, body, db)


@router.put("/ee2ee-public-key")
async def update_e2ee_public_key(
    body:    UpdateE2EEPublicKeyRequest,
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    return await app_controller.update_e2ee_public_key(request, body, db)


@router.get("/bookmarks")
async def get_bookmarks(
    request: Request,
    params:  GetBookmarksSchema = Depends(),
    db:      AsyncSession = Depends(get_db),
):
    return await app_controller.get_bookmarks(request, params, db)


@router.post("/sync-contacts")
async def sync_contacts(
    body:    SyncContactsRequest,
    request: Request,
    db:      AsyncSession = Depends(get_db),
):
    return await app_controller.sync_contacts(request, body, db)


@router.get("/search-chats")
async def search_chats(
    request: Request,
    params:  SearchChatsRequest = Depends(),
    db:      AsyncSession = Depends(get_db),
):
    return await app_controller.search_chats(request, params, db)


@router.get("/lookup/phone")
async def search_by_number(
    request: Request,
    params:  LookupByPhoneRequest = Depends(),
    db:      AsyncSession = Depends(get_db),
):
    return await app_controller.search_by_number(request, params, db)