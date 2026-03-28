import io
import uuid
from datetime import datetime, timezone
from PIL import Image

from fastapi import Request

from models.common import Country, State
from schemas.used_product_listing_schemas import (
    GuestGetUsedProductListingsSchema,

    GetUsedProductListingsSchema,
    PublishUsedProductListingStateOptionsSchema,
    UsedProductListingIdParam,
    GetUserProfileUsedProductListingsSchema,
    GetUsedProductListingsByUserIdSchema,
    GetPublishedUsedProductListingsSchema,
    CreateUsedProductListingSchema,
    UpdateUsedProductListingSchema,
    UsedProductListingsSearchSuggestionsSchema
)

from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, or_, and_, exists
from sqlalchemy.dialects.mysql import insert, match
from sqlalchemy.orm import selectinload

from models.used_product_listing import UsedProductListing, UsedProductListingImage, UsedProductListingLocation, UsedProductListingSearchQuery
from models.user import User, UserLocation
from models.chat import ChatInfo
from models.bookmark import UserBookmarkUsedProductListing

from config import PROFILE_BASE_URL, MEDIA_BASE_URL, BASE_URL
from helpers.response_helper import send_json_response, send_error_response
from utils.pagination.cursor import encode_cursor, decode_cursor
from utils.aws_s3 import upload_to_s3, delete_from_s3, delete_directory_from_s3

def _fmt_url(base, path):
    return f"{base}/{path}" if path else ""

def _user_used_product_listing_summary_response(
    used_product_listing:  UsedProductListing,
    is_bookmarked: bool = False,
    distance:     float | None = None,
) -> dict:
    return {
         "user": {
            "user_id":               used_product_listing.owner.user_id,
            "first_name":            used_product_listing.owner.first_name,
            "last_name":             used_product_listing.owner.last_name,
            "is_verified":           bool(used_product_listing.owner.is_email_verified),
            "profile_pic_url":       _fmt_url(PROFILE_BASE_URL, used_product_listing.owner.profile_pic_url),
            "profile_pic_url_small": _fmt_url(PROFILE_BASE_URL, used_product_listing.owner.profile_pic_url_96x96),
            "online":                bool(used_product_listing.owner.chat_info.online) if used_product_listing.owner.chat_info else False,
            "joined_at":             str(used_product_listing.owner.created_at.year) if used_product_listing.owner.created_at else None,
        },
        "used_product_listing": {
            "used_product_listing_id": used_product_listing.used_product_listing_id,
            "name":                    used_product_listing.name,
            "description":             used_product_listing.description,
            "price":                   float(used_product_listing.price),
            "price_unit":              used_product_listing.price_unit,
            "slug":                    f"{BASE_URL}/used-used_product_listing/{used_product_listing.short_code}",
            "is_bookmarked":   is_bookmarked,
            "distance":        distance,
            "images": [
                {
                    "image_id":  img.id,
                    "url": _fmt_url(MEDIA_BASE_URL, img.url),
                    "width":     img.width,
                    "height":    img.height,
                    "size":      img.size,
                    "format":    img.format,
                }
                for img in sorted(used_product_listing.images, key=lambda x: x.created_at, reverse=True)
            ],
            "location": {
                "geo":           used_product_listing.location.geo,
            } if used_product_listing.location else None,
        }
    }

def _used_product_listing_detail_response(
    used_product_listing:  UsedProductListing,
    is_bookmarked: bool = False,
    distance:     float | None = None,
) -> dict:
    return {
        "user": {
            "user_id":               used_product_listing.owner.user_id,
            "first_name":            used_product_listing.owner.first_name,
            "last_name":             used_product_listing.owner.last_name,
            "is_verified":           bool(used_product_listing.owner.is_email_verified),
            "profile_pic_url":       _fmt_url(PROFILE_BASE_URL, used_product_listing.owner.profile_pic_url),
            "profile_pic_url_small": _fmt_url(PROFILE_BASE_URL, used_product_listing.owner.profile_pic_url_96x96),
            "online":                bool(used_product_listing.owner.chat_info.online) if used_product_listing.owner.chat_info else False,
            "joined_at":             str(used_product_listing.owner.created_at.year) if used_product_listing.owner.created_at else None,
        },
        "used_product_listing": {
                "used_product_listing_id": used_product_listing.used_product_listing_id,
                "name":                    used_product_listing.name,
                "description":             used_product_listing.description,
                "price":                   float(used_product_listing.price),
                "price_unit":              used_product_listing.price_unit,

                "country": {
                    "country_id":   used_product_listing.country.id,
                    "name": used_product_listing.country.name
                },

                "state": {
                    "country_id":   used_product_listing.state.country_id,
                    "state_id":   used_product_listing.state.id,
                    "name": used_product_listing.state.name
                },

                "slug":                    f"{BASE_URL}/used-used_product_listing/{used_product_listing.short_code}",
                "is_bookmarked":   is_bookmarked,
                "distance":        distance,
                "images": [
                    {
                        "image_id":  img.id,
                        "url": _fmt_url(MEDIA_BASE_URL, img.url),
                        "width":     img.width,
                        "height":    img.height,
                        "size":      img.size,
                        "format":    img.format,
                    }
                    for img in sorted(used_product_listing.images, key=lambda x: x.created_at, reverse=True)
                ],
                "location": {
                    "geo":           used_product_listing.location.geo,
                } if used_product_listing.location else None
        }
    }

def _used_product_listing_summary_response(
    used_product_listing:  UsedProductListing,
    is_bookmarked: bool = False,
    distance:     float | None = None,
) -> dict:
    return {
                "used_product_listing_id": used_product_listing.used_product_listing_id,
                "name":                    used_product_listing.name,
                "description":             used_product_listing.description,
                "price":                   float(used_product_listing.price),
                "price_unit":              used_product_listing.price_unit,
                
                "country": {
                    "country_id":   used_product_listing.country.id,
                    "name": used_product_listing.country.name
                },

                "state": {
                    "country_id":   used_product_listing.state.country_id,
                    "state_id":   used_product_listing.state.id,
                    "name": used_product_listing.state.name
                },

                "status":                  used_product_listing.status,
                "slug":                    f"{BASE_URL}/used-used_product_listing/{used_product_listing.short_code}",
                "is_bookmarked":   is_bookmarked,
                "distance":        distance,
                "images": [
                    {
                        "image_id":  img.id,
                        "url": _fmt_url(MEDIA_BASE_URL, img.url),
                        "width":     img.width,
                        "height":    img.height,
                        "size":      img.size,
                        "format":    img.format,
                    }
                    for img in sorted(used_product_listing.images, key=lambda x: x.created_at, reverse=True)
                ],
                "location": {
                    "longitude":     float(used_product_listing.location.longitude),
                    "latitude":      float(used_product_listing.location.latitude),
                    "geo":           used_product_listing.location.geo,
                    "location_type": used_product_listing.location.location_type,
                } if used_product_listing.location else None
    }

def _published_used_product_listing_response(
    used_product_listing:  UsedProductListing
) -> dict:
    return {
        "used_product_listing_id": used_product_listing.used_product_listing_id,
        "name":                    used_product_listing.name,
        "description":             used_product_listing.description,
        "price":                   float(used_product_listing.price),
        "price_unit":              used_product_listing.price_unit,
   
        "country": {
                    "country_id":   used_product_listing.country.id,
                    "name": used_product_listing.country.name
                },

        "state": {
                    "country_id":   used_product_listing.state.country_id,
                    "state_id":   used_product_listing.state.id,
                    "name": used_product_listing.state.name
                },

        "status":                  used_product_listing.status,
        "slug":                    f"{BASE_URL}/used-used_product_listing/{used_product_listing.short_code}",
        "images": [
            {
                "image_id":  img.id,
                "url": _fmt_url(MEDIA_BASE_URL, img.url),
                "width":     img.width,
                "height":    img.height,
                "size":      img.size,
                "format":    img.format,
            }
            for img in sorted(used_product_listing.images, key=lambda x: x.created_at, reverse=True)
        ],
        "location": {
            "longitude":     float(used_product_listing.location.longitude),
            "latitude":      float(used_product_listing.location.latitude),
            "geo":           used_product_listing.location.geo,
            "location_type": used_product_listing.location.location_type,
        } if used_product_listing.location else None,
    }

def _paginate_used_product_listings(items: list, used_product_listing:UsedProductListing | None, lastDistance: int | None, lastTotalRelavance: int | None,  page_size: int,  next_token: str = None ) -> dict:
    has_next       = len(items) == page_size and used_product_listing is not None
    next_token_out = encode_cursor({
        "created_at":      str(used_product_listing.created_at),
        "id":              used_product_listing.id,
        "distance":        float(lastDistance) if lastDistance is not None else None,
        "total_relevance": float(lastTotalRelavance) if lastTotalRelavance is not None else None,
    }) if has_next else None
    return {
        "data":           items,
        "next_token":     next_token_out,
        "previous_token": next_token if next_token else None,
    }

def _paginate_profile_and_used_product_listings(item: any, used_product_listing:UsedProductListing | None, page_size: int, next_token: str = None ) -> dict:
    has_next       = len(item["used_product_listings"]) == page_size and used_product_listing is not None
    next_token_out = encode_cursor({
        "created_at":      str(used_product_listing.created_at),
        "id":              used_product_listing.id
    }) if has_next else None
    return {
        "data":           item,
        "next_token":     next_token_out,
        "previous_token": next_token if next_token else None,
    }

def _paginate_used_product_listings_by_used_product_listing(items: list, used_product_listing:UsedProductListing | None, page_size: int, next_token: str = None ) -> dict:
    has_next       = len(items) == page_size and used_product_listing is not None
    next_token_out = encode_cursor({
        "created_at":      str(used_product_listing.created_at),
        "id":              used_product_listing.id
    }) if has_next else None
    return {
        "data":           items,
        "next_token":     next_token_out,
        "previous_token": next_token if next_token else None,
    }

def _haversine(lat: float, lon: float):
    return (
        6371 * func.acos(
            func.cos(func.radians(lat)) *
            func.cos(func.radians(UsedProductListingLocation.latitude)) *
            func.cos(func.radians(UsedProductListingLocation.longitude) - func.radians(lon)) +
            func.sin(func.radians(lat)) *
            func.sin(func.radians(UsedProductListingLocation.latitude))
        )
    ).label("distance")

def _relevance(query: str):
    return match(
        UsedProductListing.name,
        UsedProductListing.description,
        against=query
    ).label("total_relevance")

async def _query_used_product_listings(
    db:        AsyncSession,
    page_size: int,
    user_id:   int | None = None,
    query:     str | None = None,
    user_lat:  float | None = None,
    user_lon:  float | None = None,
    next_token: str | None = None
) -> tuple[list, any]:
    payload = decode_cursor(next_token) if next_token else None

    has_loc = user_lat is not None and user_lon is not None

    if query and not payload:
        stmt = insert(UsedProductListingSearchQuery).values(
            search_term=query,
            popularity=1,
            last_searched=datetime.now(timezone.utc),
            search_term_concatenated=query.replace(" ", ""),
        )
        stmt = stmt.on_duplicate_key_update(
            popularity=UsedProductListingSearchQuery.popularity + 1,
            last_searched=datetime.now(timezone.utc),
        )
        await db.execute(stmt)
    
    cols = [UsedProductListing]

    bookmark_subq = (
        exists()
        .where(
            UserBookmarkUsedProductListing.used_product_listing_id == UsedProductListing.used_product_listing_id,
            UserBookmarkUsedProductListing.user_id == user_id
        )
    ).label("is_bookmarked")

    if has_loc:
           distance_expr = _haversine(user_lat, user_lon)
           cols.append(distance_expr)
    if query:
            relevance_expr = _relevance(query)
            cols.append(relevance_expr)
    if user_id:
        cols.append(bookmark_subq)

    q = (
        select(*cols)
        .options(
            selectinload(UsedProductListing.images),    
            selectinload(UsedProductListing.location),
            selectinload(UsedProductListing.owner).selectinload(User.chat_info)
        )
    )

    if has_loc:
        q = q.join(
            UsedProductListingLocation,
            UsedProductListingLocation.used_product_listing_id == UsedProductListing.used_product_listing_id
        )

    if query:
        q = q.where(match(
            UsedProductListing.name,
            UsedProductListing.description,
            against=query,
        ) > 0)

    if payload:
        if has_loc and query:
                q = q.where(or_(
                    distance_expr > payload["distance"],
                    and_(distance_expr == payload["distance"], relevance_expr < payload["total_relevance"]),
                    and_(distance_expr == payload["distance"], relevance_expr == payload["total_relevance"], UsedProductListing.created_at < payload["created_at"]),
                    and_(distance_expr == payload["distance"], relevance_expr == payload["total_relevance"], UsedProductListing.created_at == payload["created_at"], UsedProductListing.id > payload["id"]),
                ))
        elif has_loc:
            q = q.where(or_(
                distance_expr > payload["distance"],
                and_(distance_expr == payload["distance"], UsedProductListing.created_at < payload["created_at"]),
                and_(distance_expr == payload["distance"], UsedProductListing.created_at == payload["created_at"], UsedProductListing.id > payload["id"]),
            ))
        elif query:
            q = q.where(or_(
                relevance_expr < payload["total_relevance"],
                and_(relevance_expr == payload["total_relevance"], UsedProductListing.created_at < payload["created_at"]),
                and_(relevance_expr == payload["total_relevance"], UsedProductListing.created_at == payload["created_at"], UsedProductListing.id > payload["id"]),
            ))
        else:
            q = q.where(or_(
                UsedProductListing.created_at < payload["created_at"],
                and_(UsedProductListing.created_at == payload["created_at"], UsedProductListing.id > payload["id"]),
            ))
    
    
    if has_loc and query:
        q = q.order_by(
            distance_expr.asc(),
            relevance_expr.desc(),
            UsedProductListing.created_at.desc(),
            UsedProductListing.id.asc()
        )
    elif has_loc:
        q = q.order_by(
            distance_expr.asc(),
            UsedProductListing.created_at.desc(),
            UsedProductListing.id.asc()
        )
    elif query:
        q = q.order_by(
            relevance_expr.desc(),
            UsedProductListing.created_at.desc(),
            UsedProductListing.id.asc()
        )
    else:
        q = q.order_by(
            UsedProductListing.created_at.desc(),
            UsedProductListing.id.asc()
        )

    q = q.limit(page_size)

    result = await db.execute(q)
    rows   = result.all()
    last_row  = None

    last_row = rows[-1] if rows else None

    usedProductListings = [
    _user_used_product_listing_summary_response(
        row.UsedProductListing,
        bool(row.is_bookmarked) if user_id else False,
        float(row.distance)     if has_loc else None
    )
    for row in rows]
    
    return _paginate_used_product_listings(
        usedProductListings,
        getattr(last_row, "UsedProductListing", None),
        getattr(last_row, "distance", None) if has_loc else None,
        getattr(last_row, "total_relevance", None) if query else None,
        page_size,
        next_token if payload else None,
    )

async def guest_get_used_product_listings(request: Request, schema: GuestGetUsedProductListingsSchema, db: AsyncSession):
    try:
        s = schema.s
        page_size = schema.page_size
        next_token = schema.next_token
        
        lat = schema.latitude
        lon = schema.longitude

        data = await _query_used_product_listings(db=db, page_size=page_size, query=s, user_lat=lat, user_lon=lon, next_token=next_token)
        return send_json_response(200, "Local usedProductListings fetched", data= data)
    except Exception:
        return send_error_response(request, 500, "Internal server error")
    
async def get_used_product_listings(request: Request, schema: GetUsedProductListingsSchema, db: AsyncSession):
    try:
        s = schema.s
        page_size = schema.page_size
        next_token = schema.next_token
        
        user_id = request.state.user.user_id    

        loc = await db.scalar(select(UserLocation).where(UserLocation.user_id == user_id))
        lat, lon = (float(loc.latitude), float(loc.longitude)) if loc else (None, None)

        data = await _query_used_product_listings(db=db, user_id=user_id, page_size=page_size, query=s, user_lat=lat, user_lon=lon, next_token=next_token)
        return send_json_response(200, "Local usedProductListings fetched", data= data)
    except Exception:
        return send_error_response(request, 500, "Internal server error")    

async def get_used_product_listing_by_used_product_listing_id(request: Request, schema: UsedProductListingIdParam, db: AsyncSession):
    try:
        used_product_listing = await db.scalar(
            select(UsedProductListing)
            .options(
                selectinload(UsedProductListing.images),
                selectinload(UsedProductListing.location),
                selectinload(UsedProductListing.owner).selectinload(User.chat_info)
            )
            .where(UsedProductListing.used_product_listing_id == schema.used_product_listing_id)
        )

        if not used_product_listing:
            return send_error_response(request, 404, "Used product listing not exist")
        data=_used_product_listing_detail_response(used_product_listing)
         
        data["contact_info"] = {
            "phone_country_code": used_product_listing.owner.phone_country_code,
            "phone_number":       used_product_listing.owner.phone_number,
        }
        return send_json_response(200, "Used product listing retrived", data = data)
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def get_user_profile_and_used_product_listings(
    request: Request,
    schema: GetUserProfileUsedProductListingsSchema,
    db: AsyncSession,
): 
    try:
        user_id = request.state.user.user_id
        page_size = schema.page_size
        
        bookmark_subq = (
            exists()
            .where(
                UserBookmarkUsedProductListing.used_product_listing_id == UsedProductListing.used_product_listing_id,
                UserBookmarkUsedProductListing.user_id == user_id
            )
        ).label("is_bookmarked")
        
        q = (
            select(UsedProductListing, bookmark_subq)
            .where(UsedProductListing.created_by == user_id)
            .options(
                selectinload(UsedProductListing.images),      
                selectinload(UsedProductListing.location),   
                selectinload(UsedProductListing.owner)      
            )
        )

        q = q.order_by(UsedProductListing.created_at.desc(), UsedProductListing.id.asc()).limit(page_size)

        usedProductListings = (await db.execute(q)).all()

        owner = usedProductListings[0].UsedProductListing if usedProductListings else None
        chat  = owner.chat_info if owner else None

        items = [_used_product_listing_summary_response(used_product_listing) for used_product_listing in usedProductListings]

        data = {
            "user": {
                "user_id":               owner.user_id               if owner else None,
                "first_name":            owner.first_name            if owner else None,
                "last_name":             owner.last_name             if owner else None,
                "is_verified":           bool(owner.is_email_verified) if owner else False,
                "profile_pic_url":       _fmt_url(PROFILE_BASE_URL, owner.profile_pic_url)       if owner else None,
                "profile_pic_url_small": _fmt_url(PROFILE_BASE_URL, owner.profile_pic_url_96x96) if owner else None,
                "online":                bool(chat.online) if chat else False,
                "joined_at":             str(owner.created_at.year) if owner and owner.created_at else None,
            },
            "used_product_listings": items,
        }
        last_row = usedProductListings[-1] if usedProductListings else None   
        return send_json_response(
            200,
            "User profile and Used product listings retrieved",
            data=_paginate_profile_and_used_product_listings(data, last_row.UsedProductListing, page_size))
    except Exception:
            return send_error_response(request, 500, "Internal server error")

async def get_used_product_listings_by_user_id(
    request: Request,
    schema: GetUsedProductListingsByUserIdSchema,
    db: AsyncSession,
): 
    try:
        user_id = request.state.user.user_id
        next_token = schema.next_token
        page_size = schema.page_size
        payload = decode_cursor(next_token) if next_token else None

        bookmark_subq = (
            exists()
            .where(
                UserBookmarkUsedProductListing.used_product_listing_id == UsedProductListing.used_product_listing_id,
                UserBookmarkUsedProductListing.user_id == user_id
            )
        ).label("is_bookmarked")

        q = (
                select(UsedProductListing, bookmark_subq)
                .where(UsedProductListing.created_by == user_id)
                .options(
                    selectinload(UsedProductListing.images),      
                    selectinload(UsedProductListing.location),   
                    selectinload(UsedProductListing.owner)      
                )
            )

        if payload:
                q = q.where(or_(
                    UsedProductListing.created_at < payload["created_at"],
                    and_(UsedProductListing.created_at == payload["created_at"], UsedProductListing.id > payload["id"]),
                ))

        q = q.order_by(UsedProductListing.created_at.desc(), UsedProductListing.id.asc()).limit(page_size)

        usedProductListings = (await db.execute(q)).scalars().all()

        items = [_user_used_product_listing_summary_response(used_product_listing, bool(is_bookmarked)) for used_product_listing, is_bookmarked in usedProductListings]
        last_row = usedProductListings[-1] if usedProductListings else None

        return send_json_response(200, "Used product listings retrieved", data=_paginate_used_product_listings_by_used_product_listing(items, last_row, page_size, next_token if payload else None))
    except Exception:
            return send_error_response(request, 500, "Internal server error")

async def create_used_product_listing(
    request: Request,
    schema:  CreateUsedProductListingSchema,
    db:      AsyncSession,
):
    images = schema.images or []
    uploaded_keys  = []
    try:
        user_id  = request.state.user.user_id
        media_id = await db.scalar(select(User.media_id).where(User.user_id == user_id))
        if not media_id:
            return send_error_response(request, 400, "Something went wrong")

        country = await db.scalar(
            select(Country).where(Country.id == schema.country)
        )
        if not country:
            return send_error_response(request, 400, "Invalid country")

        state = await db.scalar(
            select(State).where(
                State.id         == schema.state,
                State.country_id == schema.country
            )
        )
        
        if not state:
            return send_error_response(request, 400, "Invalid state")
        
        new_product = UsedProductListing(
                name             = schema.name,
                description      = schema.description,
                price_unit       = schema.price_unit,
                price            = schema.price,
                country_id          = country.id,
                state_id           = state.id,
                created_by       = user_id
                )
        db.add(new_product)
        
        await db.flush()
        
        used_product_listing = await db.scalar(
            select(UsedProductListing)
            .options(
                selectinload(UsedProductListing.images),
                selectinload(UsedProductListing.location),
                selectinload(UsedProductListing.owner),
            )  
            .where(
                UsedProductListing.used_product_listing_id == new_product.used_product_listing_id,
                UsedProductListing.created_by   == user_id
            ))
          
        old_images = used_product_listing.images
        keep_ids   = set(schema.keep_image_ids or [])
        deleted_keys   = []

        for img in old_images:
            if img.id not in keep_ids:
                deleted_keys.append(img.url) 
                await db.delete(img)

        for image in images:
            contents = await image.read()
            key      = f"media/{media_id}/used-product-listings/{used_product_listing.used_product_listing_id}/{uuid.uuid4()}-{image.filename}"
            await upload_to_s3(contents, key, image.content_type)
            uploaded_keys.append(key)

            img = Image.open(io.BytesIO(contents))
            width, height = img.size
 
            db.add(UsedProductListingImage(
                used_product_listing_id = used_product_listing.used_product_listing_id,
                url    = key,
                width        = width,
                height       = height,
                size         = len(contents),
                format       = image.content_type or "",
            ))

        await db.flush() 

        location = schema.location
        loc      = used_product_listing.location

        if loc:
            loc.latitude      = location["latitude"]
            loc.longitude     = location["longitude"]
            loc.geo           = location["geo"]
            loc.location_type = location["location_type"]
            db.add(loc)
        else:
            db.add(UsedProductListingLocation(
                used_product_listing_id  = used_product_listing.used_product_listing_id,
                latitude      = location["latitude"],
                longitude     = location["longitude"],
                geo           = location["geo"],
                location_type = location["location_type"],
            ))

        await db.flush()

        for key in deleted_keys:
            await delete_from_s3(key)

        await db.refresh(used_product_listing, attribute_names=["images", "location", "owner"])    
        return send_json_response(200, "Used product listing published", data=_published_used_product_listing_response(used_product_listing))
    except Exception:
        for key in uploaded_keys:
            await delete_from_s3(key)
        return send_error_response(request, 500, "Internal server error")

async def update_used_product_listing(
    request: Request,
    schema:  UpdateUsedProductListingSchema,
    db:      AsyncSession,
):
    images = schema.images or []
    uploaded_keys = []
    try:
        user_id  = request.state.user.user_id
        media_id = await db.scalar(select(User.media_id).where(User.user_id == user_id))
        if not media_id:
            return send_error_response(request, 400, "Something went wrong")

        existing = await db.scalar(
            select(UsedProductListing)
            .options(
                selectinload(UsedProductListing.images),
                selectinload(UsedProductListing.location),
                selectinload(UsedProductListing.owner),
            )
            .where(
                UsedProductListing.used_product_listing_id == schema.used_product_listing_id,
                UsedProductListing.created_by == user_id,
            )
        )
        if not existing:
            return send_error_response(request, 404, "Invalid product listing")

        country = await db.scalar(
            select(Country).where(Country.id == schema.country)
        )
        if not country:
            return send_error_response(request, 400, "Invalid country")

        state = await db.scalar(
            select(State).where(
                State.id == schema.state,
                State.country_id == schema.country
            )
        )
        if not state:
            return send_error_response(request, 400, "Invalid state")

        existing.name        = schema.name
        existing.description = schema.description
        existing.price_unit  = schema.price_unit
        existing.price       = schema.price
        existing.country_id  = country.id
        existing.state_id    = state.id
        db.add(existing)

        await db.flush()

        keep_ids     = set(schema.keep_image_ids or [])
        deleted_keys = []

        for img in existing.images:
            if img.id not in keep_ids:
                deleted_keys.append(img.url)
                await db.delete(img)

        for image in images:
            contents = await image.read()
            key = f"media/{media_id}/used-product-listings/{existing.used_product_listing_id}/{uuid.uuid4()}-{image.filename}"
            await upload_to_s3(contents, key, image.content_type)
            uploaded_keys.append(key)

            img = Image.open(io.BytesIO(contents))
            width, height = img.size

            db.add(UsedProductListingImage(
                used_product_listing_id = existing.used_product_listing_id,
                url    = key,
                width  = width,
                height = height,
                size   = len(contents),
                format = image.content_type or "",
            ))

        await db.flush()

        location = schema.location
        loc      = existing.location

        if loc:
            loc.latitude      = location["latitude"]
            loc.longitude     = location["longitude"]
            loc.geo           = location["geo"]
            loc.location_type = location["location_type"]
            db.add(loc)
        else:
            db.add(UsedProductListingLocation(
                used_product_listing_id = existing.used_product_listing_id,
                latitude      = location["latitude"],
                longitude     = location["longitude"],
                geo           = location["geo"],
                location_type = location["location_type"],
            ))

        await db.flush()

        for key in deleted_keys:
            await delete_from_s3(key)

        await db.refresh(existing, attribute_names=["images", "location", "owner"])
        return send_json_response(200, "Used product listing updated", data=_published_used_product_listing_response(existing))
    except Exception:
        for key in uploaded_keys:
            await delete_from_s3(key)
        return send_error_response(request, 500, "Internal server error")

async def get_published_used_product_listings(
    request: Request,
    schema: GetPublishedUsedProductListingsSchema,
    db: AsyncSession,
):
    user_id = request.state.user.user_id
    next_token = schema.next_token
    page_size = schema.page_size
    payload = decode_cursor(next_token) if next_token else None

    q = (
        select(UsedProductListing)
        .where(UsedProductListing.created_by == user_id)
        .options(
            selectinload(UsedProductListing.images),      
            selectinload(UsedProductListing.location),   
            selectinload(UsedProductListing.owner)      
        )
    )

    if payload:
        q = q.where(or_(
            UsedProductListing.created_at < payload["created_at"],
            and_(UsedProductListing.created_at == payload["created_at"], UsedProductListing.id > payload["id"]),
        ))

    q = q.order_by(UsedProductListing.created_at.desc(), UsedProductListing.id.asc()).limit(page_size)

    usedProductListings = (await db.execute(q)).scalars().all()

    items = [_published_used_product_listing_response(used_product_listing) for used_product_listing in usedProductListings]
    last_row = usedProductListings[-1] if usedProductListings else None
    return send_json_response(
        200,
        "Used product listings retrieved",
        data=_paginate_used_product_listings_by_used_product_listing(items, last_row, page_size, next_token if payload else None)
        )

async def delete_used_product_listing(request: Request, schema: UsedProductListingIdParam, db: AsyncSession):
    try:
        user    = request.state.user
        usedProductListing = await db.scalar(select(UsedProductListing).where(UsedProductListing.used_product_listing_id == schema.used_product_listing_id, UsedProductListing.created_by == user.user_id))
        if not usedProductListing:
            return send_error_response(request, 404, "Used product listing not exist")

        media = await db.scalar(select(User.media_id).where(User.user_id == user.user_id))
        await db.delete(usedProductListing)
        if media:
            await delete_directory_from_s3(f"media/{media}/used-used_product_listing-listings/{schema.used_product_listing_id}")
        return send_json_response(200, "Listing deleted")
    except Exception:
        return send_error_response(request, 500, "Internal server error")


async def get_published_used_product_listing_by_used_product_listing_id(request: Request, schema: UsedProductListingIdParam, db: AsyncSession):
    try:
        used_product_listing = await db.scalar(
            select(UsedProductListing)
            .options(
                selectinload(UsedProductListing.images),
                selectinload(UsedProductListing.location),
                selectinload(UsedProductListing.owner).selectinload(User.chat_info)
            )
            .where(UsedProductListing.used_product_listing_id == schema.used_product_listing_id)
        )

        if not used_product_listing:
            return send_error_response(request, 404, "Used product listing not exist")
        data=_published_used_product_listing_response(used_product_listing)
        return send_json_response(200, "Used product listing retrived", data = data)
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def bookmark_used_product_listing(request: Request, schema: UsedProductListingIdParam, db: AsyncSession):
    try:
        db.add(UserBookmarkUsedProductListing(user_id=request.state.user.user_id, used_product_listing_id=schema.used_product_listing_id))
        await db.flush()
        return send_json_response(200, "Bookmarked")
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def unbookmark_used_product_listing(request: Request, schema: UsedProductListingIdParam, db: AsyncSession):
    try:
        bookmark = await db.scalar(select(UserBookmarkUsedProductListing).where(UserBookmarkUsedProductListing.user_id == request.state.user.user_id, UserBookmarkUsedProductListing.used_product_listing_id == schema.used_product_listing_id))
        if not bookmark:
            return send_error_response(request, 404, "Failed to remove bookmark")
        await db.delete(bookmark)
        return send_json_response(200, "Bookmark removed")
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def used_product_listings_search_suggestions(request: Request, schema:UsedProductListingsSearchSuggestionsSchema, db: AsyncSession):
    try:
        clean  = schema.query.strip().lower()
        words  = clean.split()
        result = await db.scalars(
            select(UsedProductListingSearchQuery)
            .where(or_(
                UsedProductListingSearchQuery.search_term.ilike(f"{clean}%"),
                *[UsedProductListingSearchQuery.search_term.ilike(f"%{w}%") for w in words],
                UsedProductListingSearchQuery.search_term_concatenated.ilike(f"{clean.replace(' ', '')}%"),
            ))
            .where(UsedProductListingSearchQuery.popularity > 1)
            .order_by(UsedProductListingSearchQuery.popularity.desc())
            .limit(10)
        )
        return send_json_response(200, "Suggestions retrieved", data=[{"search_term": r.search_term} for r in result])
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def get_publish_meta_options(request: Request, db: AsyncSession):
    try:
        q = select(Country).order_by(Country.name)
        result = await db.execute(q)
        countries = result.scalars().all()

        price_units = [
            {"value": "INR", "name": "INR"},
            {"value": "USD", "name": "USD"},
        ]

        return send_json_response(
            200,
            "Meta options fetched",
            data={
                "countries": [
                    {"country_id": c.id, "name": c.name}
                    for c in countries
                ],
                "price_units": price_units
            }
        )

    except Exception as e:
        return send_error_response(request, 500, "Internal server error")

async def get_publish_countries_options(request: Request, db: AsyncSession):
    try:
        q      = select(Country).order_by(Country.name)
        result = await db.execute(q)
        countries = result.scalars().all()
        return send_json_response(200, "Countries fetched", data=[
            {"country_id": c.id, "name": c.name}
            for c in countries
        ])
    except Exception as e:
        return send_error_response(request, 500, "Internal server error")

async def get_publish_states_options(
    request: Request,
    schema:  PublishUsedProductListingStateOptionsSchema,
    db:      AsyncSession,
):
    try:
        q = select(State).where(State.country_id == schema.country_id)
        q = q.order_by(State.name).limit(50)

        result = await db.execute(q)
        states = result.scalars().all()
        return send_json_response(200, "States fetched", data=[
            {"country_id": s.country_id, "state_id": s.id,  "name": s.name}
            for s in states
        ])
    except Exception as e:
        return send_error_response(request, 500, "Internal server error")    