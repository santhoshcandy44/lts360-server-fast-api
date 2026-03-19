import json
import uuid
from datetime import datetime, timezone

from fastapi import Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from sqlalchemy import func, or_, and_, delete
from sqlalchemy.dialects.mysql import insert

from models.services import Service, ServiceThumbnail, ServiceImage, ServiceLocation , ServicePlan, ServiceSearchQuery
from models.users import UserServiceIndustry
from models.users import User, UserLocation
from models.chats import ChatInfo
from models.bookmarks import UserBookmarkService

from config import BASE_URL, PROFILE_BASE_URL, MEDIA_BASE_URL
from helpers.response_helper import send_json_response, send_error_response
from utils.pagination.cursor import encode_cursor, decode_cursor
from utils.aws_s3 import upload_to_s3, delete_from_s3, delete_directory_from_s3


# ── Shared helpers ─────────────────────────────────────────────────────────────

def _fmt_url(base, path):
    return f"{base}/{path}" if path else None


def _parse_plans(plans: list[ServicePlan]) -> list[dict]:
    return [
        {
            "plan_id":            p.id,
            "plan_name":          p.name,
            "plan_description":   p.description,
            "plan_price":         p.price,
            "price_unit":         p.price_unit,
            "plan_delivery_time": p.delivery_time,
            "duration_unit":      p.duration_unit,
            "plan_features":      json.loads(p.features) if isinstance(p.features, str) else (p.features or []),
        }
        for p in sorted(plans, key=lambda x: x.created_at)
    ]


def _parse_thumbnail(t: ServiceThumbnail | None) -> dict | None:
    if not t:
        return None
    return {
        "id":     t.thumbnail_id,
        "url":    _fmt_url(MEDIA_BASE_URL, t.image_url),
        "width":  t.width,
        "height": t.height,
        "size":   t.size,
        "format": t.format,
    }


def _service_response(
    service:      Service,
    owner:        User,
    images:       list[ServiceImage],
    plans:        list[ServicePlan],
    location:     ServiceLocation | None,
    thumbnail:    ServiceThumbnail | None,
    chat:         ChatInfo | None,
    is_bookmarked: bool = False,
    distance:     float | None = None,
) -> dict:
    return {
        "user": {
            "user_id":               owner.user_id,
            "first_name":            owner.first_name,
            "last_name":             owner.last_name,
            "is_verified":           bool(owner.is_email_verified),
            "profile_pic_url":       _fmt_url(PROFILE_BASE_URL, owner.profile_pic_url),
            "profile_pic_url_small": _fmt_url(PROFILE_BASE_URL, owner.profile_pic_url_96x96),
            "online":                bool(chat.online) if chat else False,
            "joined_at":             str(owner.created_at.year) if owner.created_at else None,
        },
        "service": {
            "service_id":        service.service_id,
            "title":             service.title,
            "short_description": service.short_description,
            "long_description":  service.long_description,
            "industry":          service.industry,
            "country":           service.country,
            "state":             service.state,
            "status":            service.status,
            "slug":              f"{BASE_URL}/service/{service.short_code}",
            "is_bookmarked":     is_bookmarked,
            "distance":          distance,
            "thumbnail":         _parse_thumbnail(thumbnail),
            "images": [
                {
                    "image_id":  img.id,
                    "image_url": _fmt_url(MEDIA_BASE_URL, img.image_url),
                    "width":     img.width,
                    "height":    img.height,
                    "size":      img.size,
                    "format":    img.format,
                }
                for img in sorted(images, key=lambda x: x.created_at, reverse=True)
            ],
            "plans":    _parse_plans(plans),
            "location": {
                "longitude":     location.longitude,
                "latitude":      location.latitude,
                "geo":           location.geo,
                "location_type": location.location_type,
            } if location else None,
        }
    }


def _paginate(items: list, last_row, page_size: int, next_token: str | None, payload, distance=None, total_relevance=None) -> dict:
    has_next       = len(items) == page_size and last_row is not None
    next_token_out = encode_cursor({
        "created_at":      str(last_row.created_at),
        "id":              last_row.id,
        "distance":        float(distance) if distance is not None else None,
        "total_relevance": float(total_relevance) if total_relevance is not None else None,
    }) if has_next else None
    return {
        "data":           items,
        "next_token":     next_token_out,
        "previous_token": next_token if payload else None,
    }


# ── Related data fetchers ──────────────────────────────────────────────────────

async def _fetch_related(db: AsyncSession, service_ids: list[int]) -> tuple[dict, dict, dict, dict]:
    images_by_id:    dict[int, list] = {}
    plans_by_id:     dict[int, list] = {}
    locations_by_id: dict[int, ServiceLocation] = {}
    thumbs_by_id:    dict[int, ServiceThumbnail] = {}

    if not service_ids:
        return images_by_id, plans_by_id, locations_by_id, thumbs_by_id

    imgs = (await db.execute(
        select(ServiceImage).where(ServiceImage.service_id.in_(service_ids)).order_by(ServiceImage.created_at.desc())
    )).scalars().all()
    for img in imgs:
        images_by_id.setdefault(img.service_id, []).append(img)

    plans = (await db.execute(
        select(ServicePlan).where(ServicePlan.service_id.in_(service_ids)).order_by(ServicePlan.created_at.asc())
    )).scalars().all()
    for p in plans:
        plans_by_id.setdefault(p.service_id, []).append(p)

    locs = (await db.execute(
        select(ServiceLocation).where(ServiceLocation.service_id.in_(service_ids))
    )).scalars().all()
    for loc in locs:
        locations_by_id[loc.service_id] = loc

    thumbs = (await db.execute(
        select(ServiceThumbnail).where(ServiceThumbnail.service_id.in_(service_ids))
    )).scalars().all()
    for t in thumbs:
        thumbs_by_id[t.service_id] = t

    return images_by_id, plans_by_id, locations_by_id, thumbs_by_id


# ── Haversine + relevance expressions ─────────────────────────────────────────

def _haversine(lat: float, lon: float):
    return (
        6371 * func.acos(
            func.cos(func.radians(lat)) *
            func.cos(func.radians(ServiceLocation.latitude)) *
            func.cos(func.radians(ServiceLocation.longitude) - func.radians(lon)) +
            func.sin(func.radians(lat)) *
            func.sin(func.radians(ServiceLocation.latitude))
        )
    ).label("distance")


def _relevance(search: str):
    return (
        func.coalesce(func.match(Service.title,             func.against(search)), 0) +
        func.coalesce(func.match(Service.short_description, func.against(search)), 0) +
        func.coalesce(func.match(Service.long_description,  func.against(search)), 0)
    ).label("total_relevance")


# ── Core query ─────────────────────────────────────────────────────────────────

async def _query_services(
    db:           AsyncSession,
    page_size:    int,
    next_token:   str | None,
    search:       str | None      = None,
    user_id:      int | None      = None,
    user_lat:     float | None    = None,
    user_lon:     float | None    = None,
    owner_id:     int | None      = None,
    industry_ids: list[int] | None = None,
    radius:       int             = 50,
    filter_by_user_industries: bool = False,
) -> tuple[list, list, any, any, float | None, float | None]:
    payload = decode_cursor(next_token) if next_token else None
    has_loc = user_lat is not None and user_lon is not None

    if search and not payload:
        stmt = insert(ServiceSearchQuery).values(
            search_term=search,
            popularity=1,
            last_searched=datetime.now(timezone.utc),
            search_term_concatenated=search.replace(" ", ""),
        )
        stmt = stmt.on_duplicate_key_update(
            popularity=ServiceSearchQuery.popularity + 1,
            last_searched=datetime.now(timezone.utc),
        )
        await db.execute(stmt)

    cols = [Service, ServiceLocation, User, ChatInfo]
    if has_loc:
        cols.append(_haversine(user_lat, user_lon))
    if search:
        cols.append(_relevance(search))
    if user_id:
        cols.append(UserBookmarkService)

    q = (
        select(*cols)
        .join(ServiceLocation, ServiceLocation.service_id == Service.service_id)
        .join(User, User.user_id == Service.created_by)
        .outerjoin(ChatInfo, ChatInfo.user_id == User.user_id)
    )

    if user_id:
        q = q.outerjoin(
            UserBookmarkService,
            and_(
                UserBookmarkService.service_id == Service.service_id,
                UserBookmarkService.user_id == user_id,
            )
        )

    if owner_id:
        q = q.where(Service.created_by == owner_id)

    if industry_ids:
        q = q.where(Service.industry.in_(industry_ids))

    if filter_by_user_industries and user_id:
        user_industry_subq = select(UserIndustry.industry_id).where(UserIndustry.user_id == user_id).scalar_subquery()
        user_industry_count = select(func.count()).where(UserIndustry.user_id == user_id).scalar_subquery()
        q = q.where(or_(user_industry_count == 0, Service.industry.in_(user_industry_subq)))

    if search:
        title_rel  = func.coalesce(func.match(Service.title,             func.against(search)), 0)
        short_rel  = func.coalesce(func.match(Service.short_description, func.against(search)), 0)
        long_rel   = func.coalesce(func.match(Service.long_description,  func.against(search)), 0)
        q = q.having(or_(title_rel > 0, short_rel > 0, long_rel > 0))

    if has_loc:
        dist_expr = _haversine(user_lat, user_lon)
        q = q.having(dist_expr < radius)

    if payload:
        if has_loc and search:
            dist_expr = _haversine(user_lat, user_lon)
            rel_expr  = _relevance(search)
            q = q.having(or_(
                dist_expr > payload["distance"],
                and_(dist_expr == payload["distance"], rel_expr < payload["total_relevance"]),
                and_(dist_expr == payload["distance"], rel_expr == payload["total_relevance"], Service.created_at < payload["created_at"]),
                and_(dist_expr == payload["distance"], rel_expr == payload["total_relevance"], Service.created_at == payload["created_at"], Service.id > payload["id"]),
            ))
        elif has_loc:
            dist_expr = _haversine(user_lat, user_lon)
            q = q.having(or_(
                dist_expr > payload["distance"],
                and_(dist_expr == payload["distance"], Service.created_at < payload["created_at"]),
                and_(dist_expr == payload["distance"], Service.created_at == payload["created_at"], Service.id > payload["id"]),
            ))
        elif search:
            rel_expr = _relevance(search)
            q = q.having(or_(
                rel_expr < payload["total_relevance"],
                and_(rel_expr == payload["total_relevance"], Service.created_at < payload["created_at"]),
                and_(rel_expr == payload["total_relevance"], Service.created_at == payload["created_at"], Service.id > payload["id"]),
            ))
        else:
            q = q.where(or_(
                Service.created_at < payload["created_at"],
                and_(Service.created_at == payload["created_at"], Service.id > payload["id"]),
            ))

    q = q.group_by(Service.service_id)

    if has_loc and search:
        q = q.order_by("distance ASC", "total_relevance DESC", Service.created_at.desc(), Service.id.asc())
    elif has_loc:
        q = q.order_by("distance ASC", Service.created_at.desc(), Service.id.asc())
    elif search:
        q = q.order_by("total_relevance DESC", Service.created_at.desc(), Service.id.asc())
    else:
        q = q.order_by(Service.created_at.desc(), Service.id.asc())

    q = q.limit(page_size)

    result = await db.execute(q)
    rows   = result.all()

    service_ids = [row[0].service_id for row in rows]
    images_by_id, plans_by_id, locations_by_id, thumbs_by_id = await _fetch_related(db, service_ids)

    items     = []
    last_row  = None
    last_dist = None
    last_rel  = None

    for i, row in enumerate(rows):
        svc      = row[0]
        loc      = row[1]
        owner    = row[2]
        chat     = row[3]
        idx      = 4
        distance = getattr(row, "distance", None) if has_loc else None
        if has_loc:
            idx += 1
        total_relevance = getattr(row, "total_relevance", None) if search else None
        if search:
            idx += 1
        bookmark = row[idx] if user_id else None

        items.append(_service_response(
            svc, owner,
            images_by_id.get(svc.service_id, []),
            plans_by_id.get(svc.service_id, []),
            loc,
            thumbs_by_id.get(svc.service_id),
            chat,
            is_bookmarked=bool(bookmark),
            distance=distance,
        ))

        if i == len(rows) - 1:
            last_row  = svc
            last_dist = distance
            last_rel  = total_relevance

    return items, rows, payload, last_row, last_dist, last_rel


# ── Get services (authenticated) ──────────────────────────────────────────────

async def get_services(
    request:     Request,
    user_id:     int,
    query_param: str | None,
    page_size:   int | None,
    next_token:  str | None,
    db:          AsyncSession,
    radius:      int = 50,
):
    try:
        page_size = page_size or 20
        loc = await db.scalar(select(UserLocation).where(UserLocation.user_id == user_id))
        lat, lon = (float(loc.latitude), float(loc.longitude)) if loc else (None, None)

        items, rows, payload, last_row, last_dist, last_rel = await _query_services(
            db, page_size, next_token, query_param,
            user_id=user_id, user_lat=lat, user_lon=lon,
            radius=radius,
            filter_by_user_industries=not bool(query_param),
        )

        if lat and lon and len(items) < page_size and radius < 200:
            return await get_services(request, user_id, query_param, page_size, next_token, db, radius + 30)

        return send_json_response(200, "Services fetched", data=_paginate(items, last_row, page_size, next_token, payload, last_dist, last_rel))
    except Exception:
        return send_error_response(request, 500, "Internal server error")


# ── Guest get services ────────────────────────────────────────────────────────

async def get_guest_services(
    request:      Request,
    query_param:  str | None,
    latitude:     float | None,
    longitude:    float | None,
    industry_ids: list[int] | None,
    page_size:    int | None,
    next_token:   str | None,
    db:           AsyncSession,
    radius:       int = 50,
):
    try:
        page_size = page_size or 20

        items, rows, payload, last_row, last_dist, last_rel = await _query_services(
            db, page_size, next_token, query_param,
            user_id=None, user_lat=latitude, user_lon=longitude,
            industry_ids=industry_ids,
            radius=radius,
        )

        if latitude and longitude and len(items) < page_size and radius < 200:
            return await get_guest_services(request, query_param, latitude, longitude, industry_ids, page_size, next_token, db, radius + 30)

        return send_json_response(200, "Services fetched", data=_paginate(items, last_row, page_size, next_token, payload, last_dist, last_rel))
    except Exception:
        return send_error_response(request, 500, "Internal server error")


# ── Get single service ─────────────────────────────────────────────────────────

async def get_service_by_service_id(request: Request, service_id: int, user_id: int | None, db: AsyncSession):
    try:
        cols = [Service, ServiceLocation, User, ChatInfo]
        if user_id:
            cols.append(UserBookmarkService)

        q = (
            select(*cols)
            .join(ServiceLocation, ServiceLocation.service_id == Service.service_id, isouter=True)
            .join(User, User.user_id == Service.created_by)
            .outerjoin(ChatInfo, ChatInfo.user_id == User.user_id)
        )
        if user_id:
            q = q.outerjoin(
                UserBookmarkService,
                and_(
                    UserBookmarkService.service_id == Service.service_id,
                    UserBookmarkService.user_id == user_id,
                )
            )

        q = q.where(Service.service_id == service_id)
        result = await db.execute(q)
        row = result.first()
        if not row:
            return send_error_response(request, 404, "Service not found")

        svc, loc, owner, chat = row[0], row[1], row[2], row[3]
        bookmark = row[4] if user_id else None

        images_by_id, plans_by_id, locations_by_id, thumbs_by_id = await _fetch_related(db, [service_id])

        return send_json_response(200, "Service fetched", data=_service_response(
            svc, owner,
            images_by_id.get(service_id, []),
            plans_by_id.get(service_id, []),
            loc,
            thumbs_by_id.get(service_id),
            chat,
            is_bookmarked=bool(bookmark),
        ))
    except Exception:
        return send_error_response(request, 500, "Internal server error")


# ── Get services by user id ────────────────────────────────────────────────────

async def _get_services_by_owner(
    request:    Request,
    owner_id:   int,
    page_size:  int | None,
    next_token: str | None,
    db:         AsyncSession,
    viewer_id:  int | None = None,
    profile:    bool = False,
):
    try:
        page_size = page_size or 20
        payload   = decode_cursor(next_token) if next_token else None

        owner = await db.scalar(select(User).where(User.user_id == owner_id))
        if not owner:
            return send_error_response(request, 404, "User not exist")

        cols = [Service, ServiceLocation, User, ChatInfo]
        if viewer_id:
            cols.append(UserBookmarkService)

        q = (
            select(*cols)
            .join(ServiceLocation, ServiceLocation.service_id == Service.service_id, isouter=True)
            .join(User, User.user_id == Service.created_by)
            .outerjoin(ChatInfo, ChatInfo.user_id == User.user_id)
        )
        if viewer_id:
            q = q.outerjoin(
                UserBookmarkService,
                and_(
                    UserBookmarkService.service_id == Service.service_id,
                    UserBookmarkService.user_id == viewer_id,
                )
            )

        q = q.where(Service.created_by == owner_id)

        if payload:
            q = q.where(or_(
                Service.created_at < payload["created_at"],
                and_(Service.created_at == payload["created_at"], Service.id > payload["id"]),
            ))

        q = q.group_by(Service.service_id).order_by(Service.created_at.desc(), Service.id.asc()).limit(page_size)

        result     = await db.execute(q)
        rows       = result.all()
        svc_ids    = [row[0].service_id for row in rows]
        images_by_id, plans_by_id, locations_by_id, thumbs_by_id = await _fetch_related(db, svc_ids)

        items    = []
        last_row = None

        for i, row in enumerate(rows):
            svc   = row[0]
            loc   = row[1]
            owner_user = row[2]
            chat  = row[3]
            bookmark = row[4] if viewer_id else None

            items.append(_service_response(
                svc, owner_user,
                images_by_id.get(svc.service_id, []),
                plans_by_id.get(svc.service_id, []),
                loc,
                thumbs_by_id.get(svc.service_id),
                chat,
                is_bookmarked=bool(bookmark),
            ))
            if i == len(rows) - 1:
                last_row = svc

        paginated = _paginate(items, last_row, page_size, next_token, payload)

        if profile:
            owner_dict = {
                "user_id":               owner.user_id,
                "first_name":            owner.first_name,
                "last_name":             owner.last_name,
                "profile_pic_url":       _fmt_url(PROFILE_BASE_URL, owner.profile_pic_url),
                "profile_pic_url_96x96": _fmt_url(PROFILE_BASE_URL, owner.profile_pic_url_96x96),
                "is_email_verified":     bool(owner.is_email_verified),
                "joined_at":             str(owner.created_at.year) if owner.created_at else None,
            }
            return send_json_response(200, "Services fetched", data={
                "data": {"user": owner_dict, "services": items},
                "next_token":     paginated["next_token"],
                "previous_token": paginated["previous_token"],
            })

        return send_json_response(200, "Services fetched", data=paginated)
    except Exception:
        return send_error_response(request, 500, "Internal server error")


async def guest_get_user_profile_and_services(request, owner_id, page_size, next_token, db):
    return await _get_services_by_owner(request, owner_id, page_size, next_token, db, profile=True)


async def get_user_profile_and_services(request, user_id, owner_id, page_size, next_token, db):
    return await _get_services_by_owner(request, owner_id, page_size, next_token, db, viewer_id=user_id, profile=True)


async def guest_get_services_by_user_id(request, owner_id, page_size, next_token, db):
    return await _get_services_by_owner(request, owner_id, page_size, next_token, db)


async def get_services_by_user_id(request, user_id, owner_id, page_size, next_token, db):
    return await _get_services_by_owner(request, owner_id, page_size, next_token, db, viewer_id=user_id)


async def get_me_services(request, user_id, page_size, next_token, db):
    return await _get_services_by_owner(request, user_id, page_size, next_token, db)


# ── Get industries ─────────────────────────────────────────────────────────────

async def get_industries(request: Request, db: AsyncSession):
    try:
        result = await db.execute(select(Industry))
        industries = result.scalars().all()
        return send_json_response(200, "Industries fetched", data=[
            {"industry_id": i.industry_id, "industry_name": i.industry_name, "description": i.description}
            for i in industries
        ])
    except Exception:
        return send_error_response(request, 500, "Internal server error")


async def get_user_industries(request: Request, user_id: int, db: AsyncSession):
    try:
        result = await db.execute(
            select(Industry)
            .join(UserIndustry, UserIndustry.industry_id == Industry.industry_id)
            .where(UserIndustry.user_id == user_id)
        )
        industries = result.scalars().all()
        return send_json_response(200, "Industries fetched", data=[
            {"industry_id": i.industry_id, "industry_name": i.industry_name, "description": i.description}
            for i in industries
        ])
    except Exception:
        return send_error_response(request, 500, "Internal server error")


async def update_industries(request: Request, user_id: int, industries_json: str, db: AsyncSession):
    try:
        industry_ids = json.loads(industries_json)
        await db.execute(delete(UserIndustry).where(UserIndustry.user_id == user_id))
        for ind_id in industry_ids:
            db.add(UserIndustry(user_id=user_id, industry_id=ind_id))
        await db.flush()
        return send_json_response(200, "Industries updated")
    except Exception:
        return send_error_response(request, 500, "Internal server error")


# ── Create service ─────────────────────────────────────────────────────────────

async def create_service(
    request:           Request,
    user_id:           int,
    title:             str,
    short_description: str,
    long_description:  str,
    industry:          int,
    country:           str,
    state:             str,
    thumbnail:         UploadFile,
    plans_json:        str,
    files:             list[UploadFile],
    location_json:     str,
    db:                AsyncSession,
):
    uploaded_keys = []
    try:
        media_id = await db.scalar(select(User.media_id).where(User.user_id == user_id))
        if not media_id:
            return send_error_response(request, 400, "Unable to retrieve media_id")

        new_service = Service(
            created_by=user_id,
            title=title,
            short_description=short_description,
            long_description=long_description,
            industry=industry,
            country=country,
            state=state,
        )
        db.add(new_service)
        await db.flush()
        service_id = new_service.service_id

        # upload images
        for file in files:
            contents = await file.read()
            key      = f"media/{media_id}/services/{service_id}/{uuid.uuid4()}-{file.filename}"
            await upload_to_s3(contents, key, file.content_type)
            uploaded_keys.append(key)
            db.add(ServiceImage(
                service_id=service_id, image_url=key,
                width=0, height=0, size=len(contents), format=file.content_type or "",
            ))

        # upload thumbnail
        thumb_contents = await thumbnail.read()
        thumb_key      = f"media/{media_id}/services/{service_id}/{uuid.uuid4()}-{thumbnail.filename}"
        await upload_to_s3(thumb_contents, thumb_key, thumbnail.content_type)
        uploaded_keys.append(thumb_key)
        db.add(ServiceThumbnail(
            service_id=service_id, image_url=thumb_key,
            width=0, height=0, size=len(thumb_contents), format=thumbnail.content_type or "",
        ))

        # plans
        plans = json.loads(plans_json)
        for plan in plans:
            db.add(ServicePlan(
                service_id    = service_id,
                name          = plan.get("plan_name", ""),
                description   = plan.get("plan_description", ""),
                price         = plan.get("plan_price", 0),
                price_unit    = plan.get("price_unit", ""),
                features      = json.dumps(plan.get("plan_features", [])),
                delivery_time = plan.get("plan_delivery_time", 0),
                duration_unit = plan.get("duration_unit", ""),
            ))

        # location
        location = json.loads(location_json)
        db.add(ServiceLocation(
            service_id    = service_id,
            longitude     = location["longitude"],
            latitude      = location["latitude"],
            geo           = location["geo"],
            location_type = location.get("locationType", location.get("location_type", "")),
        ))

        await db.flush()
        return send_json_response(200, "Service created", data={"service_id": service_id})

    except Exception:
        for key in uploaded_keys:
            await delete_from_s3(key)
        return send_error_response(request, 500, "Internal server error")


# ── Update service info ────────────────────────────────────────────────────────

async def update_service_info(
    request:           Request,
    user_id:           int,
    service_id:        int,
    title:             str,
    short_description: str,
    long_description:  str,
    industry:          int,
    db:                AsyncSession,
):
    try:
        service = await db.scalar(
            select(Service).where(Service.service_id == service_id, Service.created_by == user_id)
        )
        if not service:
            return send_error_response(request, 404, "Service not found")

        service.title             = title
        service.short_description = short_description
        service.long_description  = long_description
        service.industry          = industry
        db.add(service)
        await db.flush()

        return send_json_response(200, "Service updated", data={
            "service_id":        service.service_id,
            "title":             service.title,
            "short_description": service.short_description,
            "long_description":  service.long_description,
            "industry":          service.industry,
            "country":           service.country,
            "status":            service.status,
        })
    except Exception:
        return send_error_response(request, 500, "Internal server error")


# ── Update service thumbnail ───────────────────────────────────────────────────

async def update_service_thumbnail(
    request:    Request,
    user_id:    int,
    service_id: int,
    image_id:   int,
    file:       UploadFile,
    db:         AsyncSession,
):
    uploaded_key = None
    try:
        service = await db.scalar(
            select(Service).where(Service.service_id == service_id, Service.created_by == user_id)
        )
        if not service:
            return send_error_response(request, 404, "Service not found")

        media_id = await db.scalar(select(User.media_id).where(User.user_id == user_id))
        if not media_id:
            return send_error_response(request, 400, "Unable to retrieve media_id")

        contents     = await file.read()
        new_key      = f"media/{media_id}/services/{service_id}/{uuid.uuid4()}-{file.filename}"
        await upload_to_s3(contents, new_key, file.content_type)
        uploaded_key = new_key

        existing = await db.scalar(
            select(ServiceThumbnail).where(ServiceThumbnail.service_id == service_id)
        )
        if existing:
            old_key = existing.image_url
            existing.image_url = new_key
            existing.size      = len(contents)
            existing.format    = file.content_type or ""
            db.add(existing)
            await db.flush()
            await delete_from_s3(old_key)
        else:
            db.add(ServiceThumbnail(
                service_id=service_id, image_url=new_key,
                width=0, height=0, size=len(contents), format=file.content_type or "",
            ))
            await db.flush()

        thumb = await db.scalar(select(ServiceThumbnail).where(ServiceThumbnail.service_id == service_id))
        return send_json_response(200, "Thumbnail updated", data=_parse_thumbnail(thumb))
    except Exception:
        if uploaded_key:
            await delete_from_s3(uploaded_key)
        return send_error_response(request, 500, "Internal server error")


# ── Update service images ──────────────────────────────────────────────────────

async def update_service_images(
    request:         Request,
    user_id:         int,
    service_id:      int,
    keep_image_ids:  list[int],
    files:           list[UploadFile] | None,
    db:              AsyncSession,
):
    uploaded_keys = []
    try:
        service = await db.scalar(
            select(Service).where(Service.service_id == service_id, Service.created_by == user_id)
        )
        if not service:
            return send_error_response(request, 404, "Service not found")

        media_id = await db.scalar(select(User.media_id).where(User.user_id == user_id))
        if not media_id:
            return send_error_response(request, 400, "Unable to retrieve media_id")

        old_images = (await db.execute(
            select(ServiceImage).where(ServiceImage.service_id == service_id)
        )).scalars().all()

        for img in old_images:
            if img.id not in keep_image_ids:
                await delete_from_s3(img.image_url)
                await db.delete(img)

        for file in (files or []):
            contents = await file.read()
            key      = f"media/{media_id}/services/{service_id}/{uuid.uuid4()}-{file.filename}"
            await upload_to_s3(contents, key, file.content_type)
            uploaded_keys.append(key)
            db.add(ServiceImage(
                service_id=service_id, image_url=key,
                width=0, height=0, size=len(contents), format=file.content_type or "",
            ))

        await db.flush()

        updated = (await db.execute(
            select(ServiceImage).where(ServiceImage.service_id == service_id)
        )).scalars().all()

        return send_json_response(200, "Images updated", data=[
            {
                "image_id":  img.id,
                "image_url": _fmt_url(MEDIA_BASE_URL, img.image_url),
                "width":     img.width,
                "height":    img.height,
                "size":      img.size,
                "format":    img.format,
            }
            for img in updated
        ])
    except Exception:
        for key in uploaded_keys:
            await delete_from_s3(key)
        return send_error_response(request, 500, "Internal server error")


# ── Update service plans ───────────────────────────────────────────────────────

async def update_service_plans(
    request:    Request,
    user_id:    int,
    service_id: int,
    plans_json: str,
    db:         AsyncSession,
):
    try:
        service = await db.scalar(
            select(Service).where(Service.service_id == service_id, Service.created_by == user_id)
        )
        if not service:
            return send_error_response(request, 404, "Service not found")

        plans_data = json.loads(plans_json)

        existing_plans = (await db.execute(
            select(ServicePlan).where(ServicePlan.service_id == service_id)
        )).scalars().all()
        existing_ids = {p.id for p in existing_plans}

        valid_ids = set()
        for plan in plans_data:
            plan_id = plan.get("plan_id", -1)
            name          = plan.get("plan_name", "")
            description   = plan.get("plan_description", "")
            price         = plan.get("plan_price", 0)
            price_unit    = plan.get("price_unit", "")
            features      = json.dumps(plan.get("plan_features", []))
            delivery_time = plan.get("plan_delivery_time", 0)
            duration_unit = plan.get("duration_unit", "")

            existing = await db.scalar(select(ServicePlan).where(ServicePlan.id == plan_id))
            if existing:
                existing.name          = name
                existing.description   = description
                existing.price         = price
                existing.price_unit    = price_unit
                existing.features      = features
                existing.delivery_time = delivery_time
                existing.duration_unit = duration_unit
                db.add(existing)
                valid_ids.add(existing.id)
            else:
                new_plan = ServicePlan(
                    service_id=service_id, name=name, description=description,
                    price=price, price_unit=price_unit, features=features,
                    delivery_time=delivery_time, duration_unit=duration_unit,
                )
                db.add(new_plan)
                await db.flush()
                valid_ids.add(new_plan.id)

        # delete plans not in valid_ids
        for old_plan in existing_plans:
            if old_plan.id not in valid_ids:
                await db.delete(old_plan)

        await db.flush()

        updated = (await db.execute(
            select(ServicePlan).where(ServicePlan.service_id == service_id).order_by(ServicePlan.created_at.asc())
        )).scalars().all()

        return send_json_response(200, "Plans updated", data=_parse_plans(updated))
    except Exception:
        return send_error_response(request, 500, "Internal server error")


# ── Update service location ────────────────────────────────────────────────────

async def update_service_location(
    request:       Request,
    user_id:       int,
    service_id:    int,
    latitude:      float,
    longitude:     float,
    geo:           str,
    location_type: str,
    db:            AsyncSession,
):
    try:
        service = await db.scalar(
            select(Service).where(Service.service_id == service_id, Service.created_by == user_id)
        )
        if not service:
            return send_error_response(request, 404, "Service not found")

        loc = await db.scalar(select(ServiceLocation).where(ServiceLocation.service_id == service_id))
        if loc:
            loc.latitude      = latitude
            loc.longitude     = longitude
            loc.geo           = geo
            loc.location_type = location_type
            db.add(loc)
        else:
            db.add(ServiceLocation(
                service_id=service_id, latitude=latitude, longitude=longitude,
                geo=geo, location_type=location_type,
            ))
        await db.flush()

        return send_json_response(200, "Location updated", data={
            "service_id":    service_id,
            "latitude":      latitude,
            "longitude":     longitude,
            "geo":           geo,
            "location_type": location_type,
        })
    except Exception:
        return send_error_response(request, 500, "Internal server error")


# ── Delete service ─────────────────────────────────────────────────────────────

async def delete_service(request: Request, user_id: int, service_id: int, db: AsyncSession):
    try:
        service = await db.scalar(
            select(Service).where(Service.service_id == service_id, Service.created_by == user_id)
        )
        if not service:
            return send_error_response(request, 404, "Service not found")

        media_id = await db.scalar(select(User.media_id).where(User.user_id == user_id))

        await db.execute(delete(ServiceImage).where(ServiceImage.service_id == service_id))
        await db.execute(delete(ServiceThumbnail).where(ServiceThumbnail.service_id == service_id))
        await db.execute(delete(ServicePlan).where(ServicePlan.service_id == service_id))
        await db.execute(delete(ServiceLocation).where(ServiceLocation.service_id == service_id))
        await db.delete(service)
        await db.flush()

        if media_id:
            await delete_directory_from_s3(f"media/{media_id}/services/{service_id}")

        return send_json_response(200, "Service deleted")
    except Exception:
        return send_error_response(request, 500, "Internal server error")


# ── Bookmark / Unbookmark ─────────────────────────────────────────────────────

async def bookmark_service(request: Request, user_id: int, service_id: int, db: AsyncSession):
    try:
        db.add(UserBookmarkService(user_id=user_id, service_id=service_id))
        await db.flush()
        return send_json_response(200, "Bookmarked")
    except Exception:
        return send_error_response(request, 500, "Internal server error")


async def unbookmark_service(request: Request, user_id: int, service_id: int, db: AsyncSession):
    try:
        bookmark = await db.scalar(
            select(UserBookmarkService).where(
                UserBookmarkService.user_id == user_id,
                UserBookmarkService.service_id == service_id,
            )
        )
        if not bookmark:
            return send_error_response(request, 404, "Bookmark not found")
        await db.delete(bookmark)
        return send_json_response(200, "Unbookmarked")
    except Exception:
        return send_error_response(request, 500, "Internal server error")


# ── Search suggestions ────────────────────────────────────────────────────────

async def search_suggestions(request: Request, query: str, db: AsyncSession):
    try:
        clean = query.strip().lower()
        words = clean.split()
        result = await db.execute(
            select(ServiceSearchQuery)
            .where(or_(
                ServiceSearchQuery.search_term.ilike(f"{clean}%"),
                *[ServiceSearchQuery.search_term.ilike(f"%{w}%") for w in words],
                ServiceSearchQuery.search_term_concatenated.ilike(f"{clean.replace(' ', '')}%"),
            ))
            .where(ServiceSearchQuery.popularity > 10)
            .order_by(ServiceSearchQuery.popularity.desc())
            .limit(10)
        )
        return send_json_response(200, "Suggestions fetched", data=[r.search_term for r in result.scalars()])
    except Exception:
        return send_error_response(request, 500, "Internal server error")