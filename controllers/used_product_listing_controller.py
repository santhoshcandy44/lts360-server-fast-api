# controllers/used_products_controller.py
import uuid
from fastapi import Request, UploadFile
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, case, or_
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.orm import selectinload
from datetime import datetime, timezone

from models.used_products.used_product_listings import UsedProductListing
from models.used_products.used_product_listing_images import UsedProductListingImage
from models.used_products.used_product_listing_location import UsedProductListingLocation
from models.used_products.used_product_listing_search_queries import UsedProductListingSearchQuery
from models.user import User
from models.user_locations import UserLocation
from models.chat_info import ChatInfo
from models.user_bookmark_used_product_listings import UserBookmarkUsedProductListing
from config import PROFILE_BASE_URL, MEDIA_BASE_URL, BASE_URL
from helpers.response_helper import send_json_response, send_error_response
from utils.pagination.cursor import encode_cursor, decode_cursor
from utils.aws_s3 import upload_to_s3, delete_from_s3, delete_directory_from_s3


# ── Shared helpers ────────────────────────────────────────────────────────────
def _fmt_url(base, path):
    return f"{base}/{path}" if path else None


def _listing_response(listing: UsedProductListing, owner: User, is_bookmarked: bool = False, distance=None) -> dict:
    return {
        "user": {
            "user_id":               owner.user_id,
            "first_name":            owner.first_name,
            "last_name":             owner.last_name,
            "is_verified":           bool(owner.is_email_verified),
            "profile_pic_url":       _fmt_url(PROFILE_BASE_URL, owner.profile_pic_url),
            "profile_pic_url_small": _fmt_url(PROFILE_BASE_URL, owner.profile_pic_url_96x96),
            "online":                bool(owner.chat_info.online) if owner.chat_info else False,
            "joined_at":             str(owner.created_at.year) if owner.created_at else None,
        },
        "used_product_listing": {
            "used_product_listing_id": listing.used_product_listing_id,
            "name":          listing.name,
            "description":   listing.description,
            "price":         listing.price,
            "price_unit":    listing.price_unit,
            "country":       listing.country,
            "state":         listing.state,
            "status":        listing.status,
            "slug":          f"{BASE_URL}/used-product/{listing.short_code}",
            "is_bookmarked": is_bookmarked,
            "distance":      distance,
            "images": [
                {
                    "image_id":  img.id,
                    "image_url": _fmt_url(MEDIA_BASE_URL, img.image_url),
                    "width":     img.width,
                    "height":    img.height,
                    "size":      img.size,
                    "format":    img.format,
                }
                for img in sorted(listing.images, key=lambda x: x.created_at, reverse=True)
            ],
            "location": {
                "longitude":     listing.location.longitude,
                "latitude":      listing.location.latitude,
                "geo":           listing.location.geo,
                "location_type": listing.location.location_type,
            } if listing.location else None,
        }
    }


def _haversine_distance(lat, lon):
    return (
        6371 * func.acos(
            func.cos(func.radians(lat)) * func.cos(func.radians(UsedProductListingLocation.latitude)) *
            func.cos(func.radians(UsedProductListingLocation.longitude) - func.radians(lon)) +
            func.sin(func.radians(lat)) * func.sin(func.radians(UsedProductListingLocation.latitude))
        )
    ).label("distance")


def _fulltext_relevance(search: str):
    return (
        func.coalesce(func.match(UsedProductListing.name, func.against(search)), 0) +
        func.coalesce(func.match(UsedProductListing.description, func.against(search)), 0)
    ).label("total_relevance")


def _paginate(items: list, rows, page_size: int, next_token: str | None, payload) -> dict:
    last           = rows[-1] if rows else None
    has_next       = len(items) == page_size and last is not None
    next_token_out = encode_cursor({
        "created_at":      str(last[0].created_at),
        "id":              last[0].id,
        "distance":        float(last.distance) if hasattr(last, "distance") else None,
        "total_relevance": float(last.total_relevance) if hasattr(last, "total_relevance") else None,
    }) if has_next else None
    return {
        "data":           items,
        "next_token":     next_token_out,
        "previous_token": next_token if payload else None,
    }


_LOAD_OPTS = [
    selectinload(UsedProductListing.images),
    selectinload(UsedProductListing.location),
    selectinload(UsedProductListing.owner).selectinload(User.chat_info),
]

async def _query_listings(
    db: AsyncSession,
    page_size: int,
    next_token: str | None,
    search: str | None = None,
    viewer_id: int | None = None,
    user_lat: float | None = None,
    user_lon: float | None = None,
    owner_id: int | None = None,
) -> tuple[list, list, any]:
    """Returns (items, rows, payload)"""
    payload   = decode_cursor(next_token) if next_token else None
    has_loc   = user_lat is not None and user_lon is not None

    if search and not payload:
        stmt = insert(UsedProductListingSearchQuery).values(
            search_term=search,
            popularity=1,
            last_searched=datetime.now(timezone.utc),
            search_term_concatenated=search.replace(" ", ""),
        )
        stmt = stmt.on_duplicate_key_update(
            popularity=UsedProductListingSearchQuery.popularity + 1,
            last_searched=datetime.now(timezone.utc),
        )
        await db.execute(stmt)

    cols = [UsedProductListing, UsedProductListingLocation, User, ChatInfo]
    if has_loc:
        cols.append(_haversine_distance(user_lat, user_lon))
    if search:
        cols.append(_fulltext_relevance(search))
    if viewer_id:
        cols.append(UserBookmarkUsedProductListing)

    q = (
        select(*cols)
        .join(UsedProductListingLocation, UsedProductListingLocation.used_product_listing_id == UsedProductListing.used_product_listing_id)
        .join(User, User.user_id == UsedProductListing.created_by)
        .outerjoin(ChatInfo, ChatInfo.user_id == User.user_id)
    )

    if viewer_id:
        q = q.outerjoin(
            UserBookmarkUsedProductListing,
            (UserBookmarkUsedProductListing.used_product_listing_id == UsedProductListing.used_product_listing_id) &
            (UserBookmarkUsedProductListing.user_id == viewer_id)
        )

    if owner_id:
        q = q.where(UsedProductListing.created_by == owner_id)

    if search:
        name_rel = func.coalesce(func.match(UsedProductListing.name, func.against(search)), 0)
        desc_rel = func.coalesce(func.match(UsedProductListing.description, func.against(search)), 0)
        q = q.having((name_rel > 0) | (desc_rel > 0))

    if payload:
        if has_loc and search:
            q = q.having(or_(
                _haversine_distance(user_lat, user_lon) > payload["distance"],
                (_haversine_distance(user_lat, user_lon) == payload["distance"]) & (_fulltext_relevance(search) < payload["total_relevance"]),
                (_haversine_distance(user_lat, user_lon) == payload["distance"]) & (_fulltext_relevance(search) == payload["total_relevance"]) & (UsedProductListing.created_at < payload["created_at"]),
                (_haversine_distance(user_lat, user_lon) == payload["distance"]) & (_fulltext_relevance(search) == payload["total_relevance"]) & (UsedProductListing.created_at == payload["created_at"]) & (UsedProductListing.id > payload["id"]),
            ))
        elif has_loc:
            q = q.having(or_(
                _haversine_distance(user_lat, user_lon) > payload["distance"],
                (_haversine_distance(user_lat, user_lon) == payload["distance"]) & (UsedProductListing.created_at < payload["created_at"]),
                (_haversine_distance(user_lat, user_lon) == payload["distance"]) & (UsedProductListing.created_at == payload["created_at"]) & (UsedProductListing.id > payload["id"]),
            ))
        elif search:
            q = q.having(or_(
                _fulltext_relevance(search) < payload["total_relevance"],
                (_fulltext_relevance(search) == payload["total_relevance"]) & (UsedProductListing.created_at < payload["created_at"]),
                (_fulltext_relevance(search) == payload["total_relevance"]) & (UsedProductListing.created_at == payload["created_at"]) & (UsedProductListing.id > payload["id"]),
            ))
        else:
            q = q.where(or_(
                UsedProductListing.created_at < payload["created_at"],
                (UsedProductListing.created_at == payload["created_at"]) & (UsedProductListing.id > payload["id"]),
            ))

    q = q.group_by(UsedProductListing.used_product_listing_id)
    if has_loc and search:
        q = q.order_by("distance ASC", "total_relevance DESC", UsedProductListing.created_at.desc(), UsedProductListing.id.asc())
    elif has_loc:
        q = q.order_by("distance ASC", UsedProductListing.created_at.desc(), UsedProductListing.id.asc())
    elif search:
        q = q.order_by("total_relevance DESC", UsedProductListing.created_at.desc(), UsedProductListing.id.asc())
    else:
        q = q.order_by(UsedProductListing.created_at.desc(), UsedProductListing.id.asc())

    q = q.limit(page_size)

    result = await db.execute(q)
    rows   = result.all()

    listing_ids = [row[0].used_product_listing_id for row in rows]
    images_result = await db.execute(
        select(UsedProductListingImage)
        .where(UsedProductListingImage.used_product_listing_id.in_(listing_ids))
        .order_by(UsedProductListingImage.created_at.desc())
    )
    images_by_id: dict[int, list] = {}
    for img in images_result.scalars():
        images_by_id.setdefault(img.used_product_listing_id, []).append(img)

    items = []
    for row in rows:
        listing  = row[0]
        loc      = row[1]
        owner    = row[2]
        chat     = row[3]
        distance = getattr(row, "distance", None)
        bookmark = row[-1] if viewer_id else None
        is_bookmarked = bool(bookmark) if viewer_id else False

        listing.images   = images_by_id.get(listing.used_product_listing_id, [])
        listing.location = loc
        owner.chat_info  = chat

        items.append(_listing_response(listing, owner, is_bookmarked, distance))

    return items, rows, payload


async def get_listings(request: Request, page_size: int, next_token: str | None, search: str | None, db: AsyncSession):
    try:
        user = request.state.user
        loc  = await db.scalar(select(UserLocation).where(UserLocation.user_id == user.user_id))
        lat, lon = (float(loc.latitude), float(loc.longitude)) if loc else (None, None)
        items, rows, payload = await _query_listings(db, page_size or 20, next_token, search, user.user_id, lat, lon)
        return send_json_response(200, "Listings fetched", data=_paginate(items, rows, page_size or 20, next_token, payload))
    except Exception:
        return send_error_response(request, 500, "Internal server error")


async def guest_get_listings(request: Request, page_size: int, next_token: str | None, search: str | None, lat: float | None, lon: float | None, db: AsyncSession):
    try:
        items, rows, payload = await _query_listings(db, page_size or 20, next_token, search, None, lat, lon)
        return send_json_response(200, "Listings fetched", data=_paginate(items, rows, page_size or 20, next_token, payload))
    except Exception:
        return send_error_response(request, 500, "Internal server error")


async def get_listing_by_id(request: Request, listing_id: int, db: AsyncSession, viewer_id: int | None = None):
    try:
        result = await db.execute(
            select(UsedProductListing, User, UserBookmarkUsedProductListing)
            .options(*_LOAD_OPTS)
            .join(User, User.user_id == UsedProductListing.created_by)
            .outerjoin(UserBookmarkUsedProductListing,
                (UserBookmarkUsedProductListing.used_product_listing_id == UsedProductListing.used_product_listing_id) &
                (UserBookmarkUsedProductListing.user_id == viewer_id)
            )
            .where(UsedProductListing.used_product_listing_id == listing_id)
        )
        row = result.first()
        if not row:
            return send_error_response(request, 404, "Listing not found")

        listing, owner, bookmark = row
        data = _listing_response(listing, owner, bool(bookmark))

        # add contact info for single listing
        data["contact_info"] = {
            "phone_country_code": owner.phone_country_code,
            "phone_number":       owner.phone_number,
        }
        return send_json_response(200, "Listing fetched", data=data)
    except Exception:
        return send_error_response(request, 500, "Internal server error")


async def get_listings_by_user(request: Request, owner_id: int, page_size: int, next_token: str | None, db: AsyncSession, viewer_id: int | None = None):
    try:
        owner = await db.scalar(select(User).where(User.user_id == owner_id))
        if not owner:
            return send_error_response(request, 404, "User not exist")

        items, rows, payload = await _query_listings(db, page_size or 20, next_token, None, viewer_id, None, None, owner_id)
        return send_json_response(200, "Listings fetched", data={
            "user": {
                "user_id":    owner.user_id,
                "first_name": owner.first_name,
                "last_name":  owner.last_name,
                "profile_pic_url": _fmt_url(PROFILE_BASE_URL, owner.profile_pic_url),
                "joined_at":  str(owner.created_at.year) if owner.created_at else None,
            },
            **_paginate(items, rows, page_size or 20, next_token, payload),
        })
    except Exception:
        return send_error_response(request, 500, "Internal server error")


async def get_my_listings(request: Request, page_size: int, next_token: str | None, db: AsyncSession):
    return await get_listings_by_user(request, request.state.user.user_id, page_size, next_token, db, request.state.user.user_id)


# ── Create / Update ───────────────────────────────────────────────────────────
async def create_or_update_listing(request: Request, body, files: list[UploadFile] | None, db: AsyncSession):
    uploaded_keys = []
    try:
        user    = request.state.user
        media   = await db.scalar(select(User.media_id).where(User.user_id == user.user_id))
        if not media:
            return send_error_response(request, 400, "Unable to retrieve media_id")

        listing_id = getattr(body, "used_product_listing_id", None)
        existing   = await db.scalar(
            select(UsedProductListing).where(
                UsedProductListing.used_product_listing_id == listing_id,
                UsedProductListing.created_by == user.user_id
            )
        ) if listing_id else None

        if existing:
            for field in ["name", "description", "price", "price_unit", "country", "state"]:
                setattr(existing, field, getattr(body, field))
            existing.updated_at = datetime.now(timezone.utc)
            db.add(existing)
            listing_id = existing.used_product_listing_id
        else:
            new = UsedProductListing(created_by=user.user_id, **{f: getattr(body, f) for f in ["name", "description", "price", "price_unit", "country", "state"]})
            db.add(new)
            await db.flush()
            listing_id = new.used_product_listing_id

        # images
        keep_ids   = set(body.keep_image_ids or [])
        old_images = await db.scalars(select(UsedProductListingImage).where(UsedProductListingImage.used_product_listing_id == listing_id))
        for img in old_images:
            if img.id not in keep_ids and existing:
                await delete_from_s3(img.image_url)
                await db.delete(img)

        for file in (files or []):
            contents = await file.read()
            key      = f"media/{media}/used-product-listings/{listing_id}/{uuid.uuid4()}-{file.filename}"
            await upload_to_s3(contents, key, file.content_type)
            uploaded_keys.append(key)
            db.add(UsedProductListingImage(used_product_listing_id=listing_id, image_url=key, width=0, height=0, size=len(contents), format=file.content_type or ""))

        # location
        loc = await db.scalar(select(UsedProductListingLocation).where(UsedProductListingLocation.used_product_listing_id == listing_id))
        if loc:
            for field in ["latitude", "longitude", "geo", "location_type"]:
                setattr(loc, field, getattr(body.location, field))
        else:
            db.add(UsedProductListingLocation(used_product_listing_id=listing_id, **{f: getattr(body.location, f) for f in ["latitude", "longitude", "geo", "location_type"]}))

        await db.flush()
        return await get_listing_by_id(request, listing_id, db, user.user_id)

    except Exception:
        for key in uploaded_keys:
            await delete_from_s3(key)
        return send_error_response(request, 500, "Internal server error")


# ── Delete ────────────────────────────────────────────────────────────────────
async def delete_listing(request: Request, listing_id: int, db: AsyncSession):
    try:
        user    = request.state.user
        listing = await db.scalar(select(UsedProductListing).where(UsedProductListing.used_product_listing_id == listing_id, UsedProductListing.created_by == user.user_id))
        if not listing:
            return send_error_response(request, 404, "Listing not found")

        media = await db.scalar(select(User.media_id).where(User.user_id == user.user_id))
        await db.delete(listing)
        if media:
            await delete_directory_from_s3(f"media/{media}/used-product-listings/{listing_id}")
        return send_json_response(200, "Listing deleted")
    except Exception:
        return send_error_response(request, 500, "Internal server error")


# ── Bookmark / Unbookmark ─────────────────────────────────────────────────────
async def bookmark_listing(request: Request, listing_id: int, db: AsyncSession):
    try:
        db.add(UserBookmarkUsedProductListing(user_id=request.state.user.user_id, used_product_listing_id=listing_id))
        await db.flush()
        return send_json_response(200, "Bookmarked")
    except Exception:
        return send_error_response(request, 500, "Internal server error")


async def unbookmark_listing(request: Request, listing_id: int, db: AsyncSession):
    try:
        bookmark = await db.scalar(select(UserBookmarkUsedProductListing).where(UserBookmarkUsedProductListing.user_id == request.state.user.user_id, UserBookmarkUsedProductListing.used_product_listing_id == listing_id))
        if not bookmark:
            return send_error_response(request, 404, "Bookmark not found")
        await db.delete(bookmark)
        return send_json_response(200, "Unbookmarked")
    except Exception:
        return send_error_response(request, 500, "Internal server error")


# ── Search suggestions ────────────────────────────────────────────────────────
async def search_suggestions(request: Request, query: str, db: AsyncSession):
    try:
        clean  = query.strip().lower()
        words  = clean.split()
        result = await db.scalars(
            select(UsedProductListingSearchQuery)
            .where(or_(
                UsedProductListingSearchQuery.search_term.ilike(f"{clean}%"),
                *[UsedProductListingSearchQuery.search_term.ilike(f"%{w}%") for w in words],
                UsedProductListingSearchQuery.search_term_concatenated.ilike(f"{clean.replace(' ', '')}%"),
            ))
            .where(UsedProductListingSearchQuery.popularity > 10)
            .order_by(UsedProductListingSearchQuery.popularity.desc())
            .limit(10)
        )
        return send_json_response(200, "Suggestions", data=[r.search_term for r in result])
    except Exception:
        return send_error_response(request, 500, "Internal server error")