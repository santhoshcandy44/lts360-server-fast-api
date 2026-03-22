import json
from datetime import datetime, timezone
from fastapi import Request
from sqlmodel import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, case, literal, union_all, null
from sqlalchemy.dialects.mysql import insert

from models.user import User, UserLocation, FCMToken
from models.chat import E2EEPublicKey, ChatInfo
from models.service import Service, ServiceIndustry, ServiceLocation, ServiceThumbnail, ServiceImage, ServicePlan 
from models.used_product_listing import UsedProductListing, UsedProductListingImage, UsedProductListingLocation
from models.local_job import LocalJob, LocalJobImage, LocalJobLocation
from models.bookmark import UserBookmarkService, UserBookmarkUsedProductListing, UserBookmarkLocalJob
from config import PROFILE_BASE_URL, MEDIA_BASE_URL, BASE_URL

from helpers.response_helper import send_json_response, send_error_response
from utils.pagination.cursor import encode_cursor, decode_cursor

def _fmt_url(base, path):
    return f"{base}/{path}" if path else ""

def _parse_thumbnail(raw):
    if not raw:
        return None
    t = json.loads(raw)
    return {
        "thumbnail_id": t["thumbnail_id"],
        "url":          _fmt_url(MEDIA_BASE_URL, t["url"]),
        "width":        t["width"],
        "height":       t["height"],
        "size":         t["size"],
        "format":       t["format"],
    }

def _parse_images(raw):
    if not raw:
        return []
    return [
        {
            "image_id":  img["image_id"],
            "url": _fmt_url(MEDIA_BASE_URL, img["url"]),
            "width":     img["width"],
            "height":    img["height"],
            "size":      img["size"],
            "format":    img["format"],
        }
        for img in json.loads(raw) if img
    ]

def _parse_plans(raw):
    if not raw:
        return []
    return [
        {
            "plan_id":       p["plan_id"],
            "name":          p["name"],
            "description":   p["description"],
            "price":         float(p["price"]),
            "price_unit":    p["price_unit"],
            "features":      json.loads(p["features"]) if isinstance(p.get("features"), str) else p.get("features", []),
            "delivery_time": p["delivery_time"],
            "duration_unit": p["duration_unit"],
        }
        for p in json.loads(raw) if p
    ]

def _parse_location(row) -> dict | None:
    if getattr(row, "longitude", None) and getattr(row, "latitude", None):
        return {
            "geo":           row.geo
        }
    return None

def _agg_images(ImageModel):
    return func.coalesce(
        func.concat(
            "[",
            func.group_concat(
               func.distinct(
                    func.json_object(
                        "image_id", ImageModel.id,
                        "url", ImageModel.url,
                        "width", ImageModel.width,
                        "height", ImageModel.height,
                        "size", ImageModel.size,
                        "format", ImageModel.format,
                    )
                ).op("ORDER BY")(ImageModel.created_at.desc()) 
            ),
            "]"
        ),
        "[]"
    )

async def update_fcm_token(request: Request, body, db: AsyncSession):
    try:
        user_id = request.state.user.user_id
        stmt = insert(FCMToken).values(user_id=user_id, fcm_token=body.token)
        stmt = stmt.on_duplicate_key_update(
            fcm_token=stmt.inserted.fcm_token,
            updated_at=datetime.now(timezone.utc),
        )
        await db.execute(stmt)
        return send_json_response(200, "FCM token updated successfully")
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def update_e2ee_public_key(request: Request, body, db: AsyncSession):
    try:
        user_id = request.state.user.user_id
        stmt = insert(E2EEPublicKey).values(
            user_id=user_id,
            encrypted_public_key=body.public_key,
            key_version=body.key_version,
        )
        stmt = stmt.on_duplicate_key_update(
            encrypted_public_key=stmt.inserted.encrypted_public_key,
            key_version=stmt.inserted.key_version,
            updated_at=datetime.now(timezone.utc),
        )
        await db.execute(stmt)
        return send_json_response(200, "E2EE public key updated successfully")
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def get_bookmarks(request: Request, params, db: AsyncSession):
    try:

        user_id   = request.state.user.user_id
        page_size = params.page_size
        next_token = params.next_token 
        previous_token = params.previous_token 

        svc_plans = func.coalesce(
            func.concat(
                "[",
                func.group_concat(
                    func.distinct(
                        func.json_object(
                                "plan_id", ServicePlan.id,
                                "name", ServicePlan.name,
                                "description", ServicePlan.description,
                                "price", ServicePlan.price,
                                "price_unit", ServicePlan.price_unit,
                                "features", ServicePlan.features,
                                "delivery_time", ServicePlan.delivery_time,
                                "duration_unit", ServicePlan.duration_unit,
                            )
                    ).op("ORDER BY")(ServicePlan.created_at.asc()) 
                ),
                "]"
            ),
            "[]"
        ).label("plans")

        svc_thumbnail = case(
            (ServiceThumbnail.id.isnot(None), func.json_object(
                "thumbnail_id", ServiceThumbnail.id,
                "url", ServiceThumbnail.url,
                "width", ServiceThumbnail.width,
                "height", ServiceThumbnail.height,
                "size", ServiceThumbnail.size,
                "format", ServiceThumbnail.format,
            )),
            else_=None
        ).label("thumbnail")

        services_q = (
            select(
                literal("service").label("type"),
                Service.service_id.label("item_id"),
                Service.id.label("id"),
                literal(0).label("p_type"),
                Service.title,
                Service.short_description,
                Service.long_description,
                ServiceIndustry.industry_id.label("industry"),
                Service.short_code,
                Service.country,
                Service.state,
                null().label("images"),
                svc_plans,
                svc_thumbnail,

                User.user_id.label("publisher_id"),
                User.first_name.label("publisher_first_name"),
                User.last_name.label("publisher_last_name"),
                User.profile_pic_url.label("publisher_profile_pic_url"),
                User.profile_pic_url_96x96.label("publisher_profile_pic_url_96x96"),
                User.created_at.label("publisher_created_at"),
                ChatInfo.online.label("user_online_status"),

                literal(True).label("is_bookmarked"),
                UserBookmarkService.created_at.label("bookmarked_at"),

                null().label("name"),
                null().label("description"),
                null().label("price"),
                null().label("price_unit"),
                null().label("company"),
                null().label("age_min"),
                null().label("age_max"),
                null().label("marital_statuses"),
                null().label("salary_unit"),
                null().label("salary_min"),
                null().label("salary_max"),
                ServiceLocation.geo.label("geo"),
            )
            .join(ServiceIndustry, ServiceIndustry.industry_id == Service.industry)
            .outerjoin(ServiceThumbnail, ServiceThumbnail.service_id == Service.service_id)
            .outerjoin(ServicePlan, ServicePlan.service_id == Service.service_id)
            .outerjoin(ServiceLocation, ServiceLocation.service_id == Service.service_id)
            .join(User, User.user_id == Service.created_by)
            .outerjoin(ChatInfo, ChatInfo.user_id == User.user_id)
            .join(UserBookmarkService, (UserBookmarkService.service_id == Service.service_id) & (UserBookmarkService.user_id == user_id))
            .where(UserBookmarkService.user_id == user_id)
            .group_by(Service.service_id)
        )

        used_products_q = (
            select(
                literal("used_product_listing").label("type"),
                UsedProductListing.used_product_listing_id.label("item_id"),
                UsedProductListing.id.label("id"),
                literal(1).label("p_type"),
                null().label("title"),
                null().label("short_description"),
                null().label("long_description"),
                null().label("industry"),
                UsedProductListing.short_code,
                UsedProductListing.country,
                UsedProductListing.state,
                _agg_images(UsedProductListingImage).label("images"),
                null().label("plans"),
                null().label("thumbnail"),
                
                User.user_id.label("publisher_id"),
                User.first_name.label("publisher_first_name"),
                User.last_name.label("publisher_last_name"),
                User.profile_pic_url.label("publisher_profile_pic_url"),
                User.profile_pic_url_96x96.label("publisher_profile_pic_url_96x96"),
                User.created_at.label("publisher_created_at"),
                ChatInfo.online.label("user_online_status"),

                literal(True).label("is_bookmarked"),
                UserBookmarkUsedProductListing.created_at.label("bookmarked_at"),

                UsedProductListing.name,
                UsedProductListing.description,
                UsedProductListing.price,
                UsedProductListing.price_unit,
                null().label("company"),
                null().label("age_min"),
                null().label("age_max"),
                null().label("marital_statuses"),
                null().label("salary_unit"),
                null().label("salary_min"),
                null().label("salary_max"),
                UsedProductListingLocation.geo.label("geo")
            )
            .outerjoin(UsedProductListingImage, UsedProductListingImage.used_product_listing_id == UsedProductListing.used_product_listing_id)
            .outerjoin(UsedProductListingLocation, UsedProductListingLocation.used_product_listing_id == UsedProductListingLocation.used_product_listing_id)
            .join(User, User.user_id == UsedProductListing.created_by)
            .outerjoin(ChatInfo, ChatInfo.user_id == User.user_id)
            .join(UserBookmarkUsedProductListing, (UserBookmarkUsedProductListing.used_product_listing_id == UsedProductListing.used_product_listing_id) & (UserBookmarkUsedProductListing.user_id == user_id))
            .where(UserBookmarkUsedProductListing.user_id == user_id)
            .group_by(UsedProductListing.used_product_listing_id)
        )
        
        local_jobs_q = (
            select(
                literal("local_job").label("type"),
                LocalJob.local_job_id.label("item_id"),
                LocalJob.id.label("id"),
                literal(2).label("p_type"),
                LocalJob.title,
                null().label("short_description"),
                null().label("long_description"),
                null().label("industry"),
                LocalJob.short_code,
                LocalJob.country,
                LocalJob.state,
                _agg_images(LocalJobImage).label("images"),
                null().label("plans"),
                null().label("thumbnail"),

                User.user_id.label("publisher_id"),
                User.first_name.label("publisher_first_name"),
                User.last_name.label("publisher_last_name"),
                User.profile_pic_url.label("publisher_profile_pic_url"),
                User.profile_pic_url_96x96.label("publisher_profile_pic_url_96x96"),
                User.created_at.label("publisher_created_at"),
                ChatInfo.online.label("user_online_status"),
                
                literal(True).label("is_bookmarked"),
                UserBookmarkLocalJob.created_at.label("bookmarked_at"),
                
                null().label("name"),
                LocalJob.description,
                null().label("price"),
                null().label("price_unit"),
                LocalJob.company,
                LocalJob.age_min,
                LocalJob.age_max,
                LocalJob.marital_statuses,
                LocalJob.salary_unit,
                LocalJob.salary_min,
                LocalJob.salary_max,
                LocalJobLocation.geo.label("geo"),
            )
            .outerjoin(LocalJobImage, LocalJobImage.local_job_id == LocalJob.local_job_id)
            .outerjoin(LocalJobLocation, LocalJobLocation.local_job_id == LocalJob.local_job_id)
            .join(User, User.user_id == LocalJob.created_by)
            .outerjoin(UserBookmarkLocalJob, (UserBookmarkLocalJob.local_job_id == LocalJob.local_job_id) & (UserBookmarkLocalJob.user_id == user_id))
            .outerjoin(ChatInfo, ChatInfo.user_id == User.user_id)
            .where(UserBookmarkLocalJob.user_id == user_id)
            .group_by(LocalJob.local_job_id)
        )

        union_q = union_all(services_q, used_products_q, local_jobs_q).subquery("all_bookmarks")

        final_q = select(union_q)

        payload = decode_cursor(next_token) if next_token else None

        if payload:
            final_q = final_q.where(
                or_(
                    union_q.c.bookmarked_at < payload["bookmarked_at"],
                    (union_q.c.bookmarked_at == payload["bookmarked_at"]) & (union_q.c.p_type > payload["p_type"]),
                    (union_q.c.bookmarked_at == payload["bookmarked_at"]) & (union_q.c.p_type == payload["p_type"]) & (union_q.c.id > payload["id"]),
                )
            )

        final_q = (
            final_q
            .order_by(union_q.c.bookmarked_at.desc(), union_q.c.p_type.asc(), union_q.c.id.asc())
            .limit(page_size)
        )

        result = await db.execute(final_q)
        rows   = result.fetchall()

        items     = {}
        last_item = None

        for index, row in enumerate(rows):
            item_key  = f"{row.type}_{row.item_id}"
            publisher = {
                "user_id":               row.publisher_id,
                "first_name":            row.publisher_first_name,
                "last_name":             row.publisher_last_name,
                "profile_pic_url":       f"{PROFILE_BASE_URL}/{row.publisher_profile_pic_url}" if row.publisher_profile_pic_url else None,
                "profile_pic_url_small": f"{PROFILE_BASE_URL}/{row.publisher_profile_pic_url_96x96}" if row.publisher_profile_pic_url else None,
                "online":                bool(row.user_online_status),
                "joined_at":             str(row.publisher_created_at.year) if row.publisher_created_at else None,
            }

            if item_key not in items:
                if row.type == "service":
                    thumbnail = _parse_thumbnail(row.thumbnail)
                    plans = _parse_plans(row.plans)
                    min_plan = min(plans, key=lambda p: p["price"]) if plans else None
                    starting_from = {
                        "price":      float(min_plan["price"]),
                        "price_unit": min_plan["price_unit"],
                    } if plans else None
                    
                    items[item_key] = {
                        "type": "service",
                        "user": publisher,
                        "service": {
                            "service_id":        row.item_id,
                            "title":             row.title,
                            "short_description": row.short_description,
                            "industry":          row.industry,
                            "slug":              f"{BASE_URL}/service/{row.short_code}",
                            "is_bookmarked":     bool(row.is_bookmarked),
                            "starting_from":     starting_from,
                            "thumbnail":         thumbnail,
                            "location":          _parse_location(row),
                        },
                    }
                elif row.type == "used_product_listing":
                    items[item_key] = {
                        "type": "used_product_listing",
                        "user": publisher,
                        "used_product_listing": {
                            "used_product_listing_id": row.item_id,
                            "name":          row.name,
                            "description":   row.description,
                            "price":         float(row.price),
                            "price_unit":    row.price_unit,
                            "slug":          f"{BASE_URL}/used-product/{row.short_code}",
                            "is_bookmarked": bool(row.is_bookmarked),
                            "images":        _parse_images(row.images),
                            "location":      _parse_location(row),
                        },
                    }
                elif row.type == "local_job":
                    items[item_key] = {
                        "type": "local_job",
                        "user": publisher,
                        "local_job": {
                            "local_job_id":      row.item_id,
                            "title":             row.title,
                            "description":       row.description,
                            "salary_unit":       row.salary_unit,
                            "salary_min":        row.salary_min,
                            "salary_max":        row.salary_max,
                            "slug":              f"{BASE_URL}/local-job/{row.short_code}",
                            "is_bookmarked":     bool(row.is_bookmarked),
                            "images":            _parse_images(row.images),
                            "location":          _parse_location(row),
                        },
                    }

            if index == len(rows) - 1:
                last_item = {
                    "bookmarked_at": row.bookmarked_at,
                    "p_type":        row.p_type,
                    "id":            row.id,
                }

        all_items      = list(items.values())
        has_next_page  = len(all_items) == page_size and last_item
        next_token_out = encode_cursor(last_item) if has_next_page and last_item else None
        prev_token_out = next_token if payload else None

        return send_json_response(200, "Bookmarks fetched", data={
            "data":           all_items,
            "next_token":     next_token_out,
            "previous_token": prev_token_out,
        })
    except Exception:
        import traceback
        import sys
        traceback.print_exc(file=sys.stderr)
        sys.stderr.flush()
        return send_error_response(request, 500, "Internal server error")

async def sync_contacts(request: Request, body, db: AsyncSession):
    try:
        user_id = request.state.user.user_id
        contacts = body.contacts
        if not contacts:
            return send_json_response(200, "Contacts synced", data=[])
        
        unique = list({
                (c.country_code, c.local_number): c
                for c in contacts
            }.values())
           
        result = await db.execute(
                select(User).where(
                    or_(*(
                        (User.phone_country_code == c.country_code) &
                        (User.phone_number == c.local_number)
                        for c in unique
                    ))
                )
            )
        users  = result.scalars().all()

        return send_json_response(200, "Contacts synced", data=[
            {
                "country_code": u.phone_country_code,
                "local_number": u.phone_number,
                "number":       f"{u.phone_country_code}{u.phone_number}",
                "user": {
                    "user_id":               u.user_id,
                    "first_name":            "You" if user_id == u.user_id else u.first_name,
                    "last_name":             "" if user_id == u.user_id else u.last_name,
                    "about":                 u.about,
                    "is_verified":           bool(u.is_email_verified) or bool(u.is_phone_verified),
                    "profile_pic_url":       f"{PROFILE_BASE_URL}/{u.profile_pic_url}" if u.profile_pic_url else None,
                    "profile_pic_url_small": f"{PROFILE_BASE_URL}/{u.profile_pic_url_96x96}" if u.profile_pic_url_96x96 else None,
                    "joined_at":             str(u.created_at.year) if u.created_at else None,
                },
            }
            for u in users
        ])
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def search_chats(request: Request, params, db: AsyncSession):
    try:
        user_id = request.state.user.user_id
        search = params.search

        loc = await db.execute(select(UserLocation).where(UserLocation.user_id == user_id))
        user_location = loc.scalar_one_or_none()
        if not user_location:
            return send_json_response(200, "Search results", data=[])

        lat = float(user_location.latitude)
        lng = float(user_location.longitude)

        distance = (
            6371 * func.acos(
                func.cos(func.radians(lat)) *
                func.cos(func.radians(UserLocation.latitude)) *
                func.cos(func.radians(UserLocation.longitude) - func.radians(lng)) +
                func.sin(func.radians(lat)) *
                func.sin(func.radians(UserLocation.latitude))
            )
        ).label("distance")

        result = await db.execute(
            select(User, distance)
            .join(UserLocation, UserLocation.user_id == User.user_id)
            .where(User.user_id != user_id)
            .where(or_(
                User.first_name.ilike(f"%{search}%"),
                User.last_name.ilike(f"%{search}%"),
            ))
            .order_by(distance.asc())
            .limit(20)
        )
        rows = result.all()

        return send_json_response(200, "Search results", data=[
            {
                "user_id":               u.user_id,
                "first_name":            u.first_name,
                "last_name":             u.last_name,
                "about":                 u.about,
                "is_verified":           bool(u.is_email_verified),
                "profile_pic_url":       f"{PROFILE_BASE_URL}/{u.profile_pic_url}" if u.profile_pic_url else None,
                "profile_pic_url_small": f"{PROFILE_BASE_URL}/{u.profile_pic_url_96x96}" if u.profile_pic_url_96x96 else None,
                "joined_at":             str(u.created_at.year) if u.created_at else None,
            }
            for u, dist in rows
        ])
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def search_by_number(request: Request, country_code: str, local_number: str, db: AsyncSession):
    try:
        user_id = request.state.user.user_id

        result = await db.execute(
            select(User)
            .where(User.phone_country_code == country_code)
            .where(User.phone_number == local_number)
            .limit(1)
        )
        user = result.scalar_one_or_none()
        if not user:
            return send_error_response(request, 404, "User not found")

        return send_json_response(200, "User found", data={
            "user_id":               user.user_id,
            "first_name":            "You" if user_id == user.user_id else user.first_name,
            "last_name":             "" if user_id == user.user_id else user.last_name,
            "about":                 user.about,
            "is_verified":           bool(user.is_email_verified),
            "profile_pic_url":       f"{PROFILE_BASE_URL}/{user.profile_pic_url}" if user.profile_pic_url else None,
            "profile_pic_url_small": f"{PROFILE_BASE_URL}/{user.profile_pic_url_96x96}" if user.profile_pic_url_96x96 else None,
            "joined_at":             str(user.created_at.year) if user.created_at else None,
        })
    except Exception:
        return send_error_response(request, 500, "Internal server error")