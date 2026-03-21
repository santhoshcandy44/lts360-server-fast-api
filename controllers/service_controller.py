import io
import json
import uuid
from datetime import datetime, timezone
from PIL import Image

from fastapi import Request

from schemas.service_schemas import (
    GuestGetServicesSchema,

    GetServicesSchema,
    ServiceIdSchema,
    GetUserProfileServicesSchema,
    GetServicesByUserIdSchema,

    CreateServiceSchema,
    GetPublishedServicesSchema,

    UpdateServiceInfoSchema,
    UpdateServiceThumbnailSchema,
    UpdateServiceImagesSchema,
    UpdateServicePlansSchema,
    UpdateServiceLocationSchema,

    ServiceSearchSuggestionsSchema,
    UpdateIndustriesSchema,
)


from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from sqlalchemy import func, or_, and_, delete
from sqlalchemy.dialects.mysql import insert, match
from sqlalchemy.orm import selectinload

from models.services import Service, ServiceIndustry, ServiceThumbnail, ServiceImage, ServiceLocation , ServicePlan, ServiceSearchQuery
from models.users import UserServiceIndustry
from models.users import User, UserLocation
from models.chats import ChatInfo
from models.bookmarks import UserBookmarkService

from config import BASE_URL, PROFILE_BASE_URL, MEDIA_BASE_URL
from helpers.response_helper import send_json_response, send_error_response
from utils.pagination.cursor import encode_cursor, decode_cursor
from utils.aws_s3 import upload_to_s3, delete_from_s3, delete_directory_from_s3

def _fmt_url(base, path):
    return f"{base}/{path}" if path else None

def _parse_plans(plans: list[ServicePlan]) -> list[dict]:
    return [
        {
            "plan_id":            p.id,
            "name":          p.name,
            "description":   p.description,
            "price":         float(p.price),
            "price_unit":         p.price_unit,
            "delivery_time": p.delivery_time,
            "duration_unit":      p.duration_unit,
            "features":      json.loads(p.features) if p.features else [],
        }
        for p in sorted(plans, key=lambda x: x.created_at)
    ]

def _parse_thumbnail(t: ServiceThumbnail | None) -> dict | None:
    if not t:
        return None
    return {
        "thumbnail_id":     t.id,
        "url":    _fmt_url(MEDIA_BASE_URL, t.image_url),
        "width":  t.width,
        "height": t.height,
        "size":   t.size,
        "format": t.format,
    }

def _user_service_summary_response(
    service:  Service,
    is_bookmarked: bool = False,
    distance:     float | None = None,
) -> dict:
    return {
         "user": {
            "user_id":               service.owner.user_id,
            "first_name":            service.owner.first_name,
            "last_name":             service.owner.last_name,
            "is_verified":           bool(service.owner.is_email_verified),
            "profile_pic_url":       _fmt_url(PROFILE_BASE_URL, service.owner.profile_pic_url),
            "profile_pic_url_small": _fmt_url(PROFILE_BASE_URL, service.owner.profile_pic_url_96x96),
            "online":                bool(service.owner.chat_info.online) if service.owner.chat_info else False,
            "joined_at":             str(service.owner.created_at.year) if service.owner.created_at else None,
        },
          "service": {
            "service_id":        service.service_id,
            "title":             service.title,
            "short_description": service.short_description,
            "industry":          service.industry,
            "slug":              f"{BASE_URL}/service/{service.short_code}",
            "is_bookmarked":     is_bookmarked,
            "distance":          distance,
            "thumbnail":         _parse_thumbnail(service.thumbnail),
            "location": {
                "geo":           service.location.geo,
            } if service.location else None,
            "starting_from": {
                    "price":      float(min(service.plans, key=lambda p: p.price).price),
                    "price_unit": min(service.plans, key=lambda p: p.price).price_unit,
                } if service.plans else None
        }
    }

def _user_service_detail_response(
    service:  Service,
    thumbnail: ServiceThumbnail,
    images:   list[ServiceImage],
    plans: list[ServicePlan],
    location: ServiceLocation,
    owner:        User,
    chat:         ChatInfo | None =  None,
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
                "geo":           location.geo,
            } if location else None,
        }
    }

def _service_summary_response(
    service:  Service,
    thumbnail: ServiceThumbnail,
    images:   list[ServiceImage],
    plans: list[ServicePlan],
    location: ServiceLocation,
    owner:        User,
    chat:         ChatInfo | None =  None,
    is_bookmarked: bool = False,
    distance:     float | None = None,
) -> dict:
    return {
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
                "longitude":     float(location.longitude),
                "latitude":      float(location.latitude),
                "geo":           location.geo,
                "location_type": location.location_type,
            } if location else None
    }

def _published_service_response(
    service:      Service,
    thumbnail:    ServiceThumbnail,
    images:       list[ServiceImage],
    plans:        list[ServicePlan],
    location:     ServiceLocation
) -> dict:
    return {
            "service_id":        service.service_id,
            "title":             service.title,
            "short_description": service.short_description,
            "long_description":  service.long_description,
            "industry":          service.industry,
            "country":           service.country,
            "state":             service.state,
            "status":            service.status,
            "slug":              f"{BASE_URL}/service/{service.short_code}",
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
                "longitude":     float(location.longitude),
                "latitude":      float(location.latitude),
                "geo":           location.geo,
                "location_type": location.location_type,
            } if location else None,
    }

def _paginate_services(items: list, service:Service | None, lastDistance: int | None, lastTotalRelavance: int | None,  page_size: int,  next_token: str = None ) -> dict:
    has_next       = len(items) == page_size and service is not None
    next_token_out = encode_cursor({
        "created_at":      str(service.created_at),
        "id":              service.id,
        "distance":        float(lastDistance) if lastDistance is not None else None,
        "total_relevance": float(lastTotalRelavance) if lastTotalRelavance is not None else None,
    }) if has_next else None
    return {
        "data":           items,
        "next_token":     next_token_out,
        "previous_token": next_token if next_token else None,
    }

def _paginate_profile_and_services(item: any, service:Service | None, page_size: int, next_token: str = None ) -> dict:
    has_next       = len(item["services"]) == page_size and service is not None
    next_token_out = encode_cursor({
        "created_at":      str(service.created_at),
        "id":              service.id
    }) if has_next else None
    return {
        "data":           item,
        "next_token":     next_token_out,
        "previous_token": next_token if next_token else None,
    }

def _paginate_services_by_service(items: list, service:Service | None, page_size: int, next_token: str = None ) -> dict:
    has_next       = len(items) == page_size and service is not None
    next_token_out = encode_cursor({
        "created_at":      str(service.created_at),
        "id":              service.id
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
            func.cos(func.radians(ServiceLocation.latitude)) *
            func.cos(func.radians(ServiceLocation.longitude) - func.radians(lon)) +
            func.sin(func.radians(lat)) *
            func.sin(func.radians(ServiceLocation.latitude))
        )
    ).label("distance")

def _relevance(query: str):
    return match(
        Service.title,
        Service.short_description,
        Service.long_description,
        against=query
    ).label("total_relevance")

async def _query_services(
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
        stmt = insert(ServiceSearchQuery).values(
            search_term=query,
            popularity=1,
            last_searched=datetime.now(timezone.utc),
            search_term_concatenated=query.replace(" ", ""),
        )
        stmt = stmt.on_duplicate_key_update(
            popularity=ServiceSearchQuery.popularity + 1,
            last_searched=datetime.now(timezone.utc),
        )
        await db.execute(stmt)
    
    cols = [Service]

    bookmark_subq = (
        select(UserBookmarkService.service_id)
        .where(UserBookmarkService.user_id == user_id)
        .correlate(UserBookmarkService)
        .scalar_subquery()
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
            selectinload(Service.images),    
            selectinload(Service.location),
            selectinload(Service.owner).selectinload(User.chat_info)
        )
    )

    if has_loc:
        q = q.join(
            ServiceLocation,
            ServiceLocation.service_id == Service.service_id
        )

    if query:
        q = q.where(match(
            Service.title,
            Service.short_description,
            Service.long_description,
            against=query
        ) > 0)

    if payload:
        if has_loc and query:
                q = q.where(or_(
                    distance_expr > payload["distance"],
                    and_(distance_expr == payload["distance"], relevance_expr < payload["total_relevance"]),
                    and_(distance_expr == payload["distance"], relevance_expr == payload["total_relevance"], Service.created_at < payload["created_at"]),
                    and_(distance_expr == payload["distance"], relevance_expr == payload["total_relevance"], Service.created_at == payload["created_at"], Service.id > payload["id"]),
                ))
        elif has_loc:
            q = q.where(or_(
                distance_expr > payload["distance"],
                and_(distance_expr == payload["distance"], Service.created_at < payload["created_at"]),
                and_(distance_expr == payload["distance"], Service.created_at == payload["created_at"], Service.id > payload["id"]),
            ))
        elif query:
            q = q.where(or_(
                relevance_expr < payload["total_relevance"],
                and_(relevance_expr == payload["total_relevance"], Service.created_at < payload["created_at"]),
                and_(relevance_expr == payload["total_relevance"], Service.created_at == payload["created_at"], Service.id > payload["id"]),
            ))
        else:
            q = q.where(or_(
                Service.created_at < payload["created_at"],
                and_(Service.created_at == payload["created_at"], Service.id > payload["id"]),
            ))
    
    
    if has_loc and query:
        q = q.order_by(
            distance_expr.asc(),
            relevance_expr.desc(),
            Service.created_at.desc(),
            Service.id.asc()
        )
    elif has_loc:
        q = q.order_by(
            distance_expr.asc(),
            Service.created_at.desc(),
            Service.id.asc()
        )
    elif query:
        q = q.order_by(
            relevance_expr.desc(),
            Service.created_at.desc(),
            Service.id.asc()
        )
    else:
        q = q.order_by(
            Service.created_at.desc(),
            Service.id.asc()
        )

    q = q.limit(page_size)

    result = await db.execute(q)
    rows   = result.all()
    last_row  = None

    last_row = rows[-1] if rows else None

    jobs = [
    _user_service_summary_response(
        row.Service,
        bool(row.is_bookmarked) if user_id else False,
        float(row.distance)     if has_loc else None
    )
    for row in rows]
    
    return _paginate_services(
        jobs,
        getattr(last_row, "Service", None),
        getattr(last_row, "distance", None) if has_loc else None,
        getattr(last_row, "total_relevance", None) if query else None,
        page_size,
        next_token if payload else None,
    )

async def guest_get_services(request: Request, schema: GuestGetServicesSchema, db: AsyncSession):
    try:
        s = schema.s
        page_size = 1
        next_token = schema.next_token
        
        lat = schema.latitude
        lon = schema.longitude

        data = await _query_services(db=db, page_size=page_size, query=s, user_lat=lat, user_long=lon, next_token=next_token)
        return send_json_response(200, "Services retrieved", data= data)
    except Exception:
        return send_error_response(request, 500, "Internal server error")
    
async def get_services(request: Request, schema: GetServicesSchema, db: AsyncSession):
    try:
        s = schema.s
        page_size = 1
        next_token = schema.next_token
        
        user_id = request.state.user.user_id    

        loc = await db.scalar(select(UserLocation).where(UserLocation.user_id == user_id))
        lat, lon = (float(loc.latitude), float(loc.longitude)) if loc else (None, None)

        data = await _query_services(db=db, user_id=user_id, page_size=page_size, query=s, user_lat=lat, user_lon=lon, next_token=next_token)
        return send_json_response(200, "Services retrived", data= data)
    except Exception:
        return send_error_response(request, 500, "Internal server error")    

async def get_service_by_service_id(request: Request, schema: ServiceIdSchema, db: AsyncSession):
    try:
        service = await db.scalar(
            select(Service)
            .options(
                selectinload(Service.images),
                selectinload(Service.location),
                selectinload(Service.owner).selectinload(User.chat_info)
            )
            .where(Service.service_id == schema.service_id)
        )

        if not service:
            return send_error_response(request, 404, "Used service listing not exist")
        data=_user_service_detail_response(
            service=service,
            thumbnail=service.thumbnail,
            images=service.images,
            plans=service.plans,
            location=service.location,
            owner=service.owner,
            chat=service.owner.chat_info
            )    
        return send_json_response(200, "Used service listing job retrived", data = data)
    except Exception:
        import traceback
        import sys
        traceback.print_exc(file=sys.stderr)
        sys.stderr.flush()
        return send_error_response(request, 500, "Internal server error")

async def get_user_profile_and_services_by_user_id(
    request: Request,
    schema: GetUserProfileServicesSchema,
    db: AsyncSession,
): 
    try:
        user_id = request.state.user.user_id
        page_size = 1
        
        q = (
            select(Service)
            .where(Service.created_by == user_id)
            .options(
                selectinload(Service.images),      
                selectinload(Service.location),   
                selectinload(Service.owner)      
            )
        )

        q = q.order_by(Service.created_at.desc(), Service.id.asc()).limit(page_size)

        services = (await db.execute(q)).scalars().all()

        owner = services[0].owner if services else None
        chat  = owner.chat_info if owner else None

        items = [_service_summary_response(service, service.thumbnail, service.images, service.plans, service.location, service.owner) for service in services]

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
            "services": items,
        }
        last_row = services[-1] if services else None   
        return send_json_response(
            200,
            "User profile and Used service listings retrieved",
            data=_paginate_profile_and_services(data, last_row, page_size))
    except Exception:
            return send_error_response(request, 500, "Internal server error")

async def get_services_by_user_id(
    request: Request,
    schema: GetServicesByUserIdSchema,
    db: AsyncSession,
): 
    try:
        next_token = schema.next_token
        page_size = 1
        payload = decode_cursor(next_token) if next_token else None

        q = (
                select(Service)
                .where(Service.created_by == schema.user_id)
                .options(
                    selectinload(Service.images),      
                    selectinload(Service.location),   
                    selectinload(Service.owner)      
                )
            )

        if payload:
                q = q.where(or_(
                    Service.created_at < payload["created_at"],
                    and_(Service.created_at == payload["created_at"], Service.id > payload["id"]),
                ))

        q = q.order_by(Service.created_at.desc(), Service.id.asc()).limit(page_size)

        services = (await db.execute(q)).scalars().all()

        items = [_published_service_response(service, service.thumbnail, service.images, service.plans, service.location) for service in services]
        last_row = services[-1] if services else None
        return send_json_response(
                200,
                "Services listings retrieved",
                data=_paginate_services_by_service(items, last_row, page_size, next_token if payload else None)
                )
    except Exception:
            import traceback
            import sys
            traceback.print_exc(file=sys.stderr)
            sys.stderr.flush()
            return send_error_response(request, 500, "Internal server error")

async def create_service(
    request: Request,
    schema:  CreateServiceSchema,
    db:      AsyncSession,
):
    images = schema.images 
    thumbnail = schema.thumbnail
    uploaded_keys  = []
    deleted_keys   = []
    try:
        user_id  = request.state.user.user_id
        media_id = await db.scalar(select(User.media_id).where(User.user_id == user_id))
        if not media_id:
            return send_error_response(request, 400, "Something went wrong")
        
        service = Service(
            title             = schema.title,
            short_description = schema.short_description,
            long_description = schema.long_description,
            industry         = schema.industry,
            country          = schema.country,
            state            = schema.state,
            created_by       = user_id
            )
        db.add(service)
        await db.flush()
        
        contents = await thumbnail.read()
        key      = f"media/{media_id}/services/{service.service_id}/{uuid.uuid4()}-{thumbnail.filename}"
        await upload_to_s3(contents, key, thumbnail.content_type)
        uploaded_keys.append(key) 

        thumb = Image.open(io.BytesIO(contents))
        width, height = thumb.size

        db.add(ServiceThumbnail(
            service_id = service.service_id,
            image_url    = key,
            width        = width,
            height       = height,
            size         = len(contents),
            format       = thumbnail.content_type or "",
        ))

        await db.flush()

        for image in images:
            contents = await image.read()
            key      = f"media/{media_id}/services/{service.service_id}/images/{uuid.uuid4()}-{image.filename}"
            await upload_to_s3(contents, key, image.content_type)
            uploaded_keys.append(key)

            img = Image.open(io.BytesIO(contents))
            width, height = img.size
 
            db.add(ServiceImage(
                service_id   = service.service_id,
                image_url    = key,
                width        = width,
                height       = height,
                size         = len(contents),
                format       = image.content_type or "",
            ))

        await db.flush() 

        for plan in schema.plans:
            db.add(ServicePlan(
            service_id  = service.service_id,
            name         = plan["name"],
            description  = plan["description"],
            price_unit   = plan["price_unit"],
            price        = plan["price"],
            features     = json.dumps(plan["features"]),
            duration_unit = plan["duration_unit"],
            delivery_time = plan["delivery_time"],
        ))

        await db.flush() 

        location = schema.location    
        db.add(ServiceLocation(
                service_id    = service.service_id,
                latitude      = location["latitude"],
                longitude     = location["longitude"],
                geo           = location["geo"],
                location_type = location["location_type"],
            ))
        
        await db.flush()

        for key in deleted_keys:
            await delete_from_s3(key)

        await db.refresh(service, attribute_names=[ "thumbnail", "images", "plans", "location", "owner"])    
        return send_json_response(200, "Service published", data=_published_service_response(service, service.thumbnail, service.images, service.plans, service.location))
    except Exception:
        for key in uploaded_keys:
            await delete_from_s3(key)
        return send_error_response(request, 500, "Internal server error")

async def get_published_services(
    request: Request,
    schema: GetPublishedServicesSchema,
    db: AsyncSession,
):
    try:
        user_id = request.state.user.user_id
        next_token = schema.next_token
        page_size = 1
        payload = decode_cursor(next_token) if next_token else None

        q = (
            select(Service)
            .where(Service.created_by == user_id)
            .options(
                selectinload(Service.thumbnail),      
                selectinload(Service.images),   
                selectinload(Service.plans),         
                selectinload(Service.location),   
                selectinload(Service.owner)      
            )
        )

        if payload:
            q = q.where(or_(
                Service.created_at < payload["created_at"],
                and_(Service.created_at == payload["created_at"], Service.id > payload["id"]),
            ))

        q = q.order_by(Service.created_at.desc(), Service.id.asc()).limit(page_size)

        services = (await db.execute(q)).scalars().all()

        items = [_published_service_response(service, service.thumbnail, service.images, service.plans, service.location) for service in services]
        last_row = services[-1] if services else None
        return send_json_response(
            200,
            "Services retrieved",
            data=_paginate_services_by_service(items, last_row, page_size, next_token if payload else None)
            )
    except Exception:
         return send_error_response(request, 500, "Internal server error")

async def update_service_info(
    request:           Request,
    schema: UpdateServiceInfoSchema,
    db:                AsyncSession,
):
    try:
        user_id = request.state.user.user_id
        service = await db.scalar(
            select(Service).where(Service.service_id == schema.service_id, Service.created_by == user_id)
        )
        if not service:
            return send_error_response(request, 404, "Service not exist")

        service.title             = schema.title
        service.short_description = schema.short_description
        service.long_description  = schema.long_description
        service.industry          = schema.industry
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

async def update_service_thumbnail(
    request:    Request,
    schema: UpdateServiceThumbnailSchema,
    db:         AsyncSession,
):
    user_id = request.state.user.user_id
    uploaded_key = None
    try:
        user_id = request.state.user.user_id
        service = await db.scalar(
            select(Service)
            .options(selectinload(Service.owner))
            .options(selectinload(Service.thumbnail))
            .where(Service.service_id == schema.service_id, Service.created_by == user_id)
        )
        if not service:
            return send_error_response(request, 404, "Service not exist")

        media_id = service.owner.media_id
        if not media_id:
            return send_error_response(request, 400, "Unable to retrieve media_id")
        
        thumbnail = schema.thumbnail
        contents     = await schema.thumbnail.read()
        new_key      = f"media/{media_id}/services/{schema.service_id}/{uuid.uuid4()}-{thumbnail.filename}"
        await upload_to_s3(contents, new_key, thumbnail.content_type)
        thumb = Image.open(io.BytesIO(contents))
        width, height = thumb.size
        uploaded_key = new_key

        existing = service.thumbnail
        if existing:
            old_key = existing.image_url
            existing.image_url = new_key
            existing.size      = len(contents)
            existing.width     = width
            existing.height    = height
            existing.format    = thumbnail.content_type or ""
            db.add(existing)
            await db.flush()
            await delete_from_s3(old_key)
        else:
            db.add(ServiceThumbnail(
                service_id=schema.service_id, image_url=new_key,
                width=width, 
                height=height, 
                size=len(contents), 
                format=thumbnail.content_type or "",
            ))
            await db.flush()

        db.refresh(service)
        return send_json_response(200, "Thumbnail updated", data=_parse_thumbnail(service.thumbnail))
    except Exception:
        if uploaded_key:
            await delete_from_s3(uploaded_key)
        return send_error_response(request, 500, "Internal server error")

async def update_service_images(
    request:         Request,
    schema: UpdateServiceImagesSchema,
    db:              AsyncSession,
):
    uploaded_keys = []
    try:
        user_id = request.state.user.user_id
        service = await db.scalar(
            select(Service)
            .options(selectinload(Service.owner))
            .options(selectinload(Service.images))
            .where(Service.service_id == schema.service_id, Service.created_by == user_id)
        )
        if not service:
            return send_error_response(request, 404, "Service not exist")

        media_id = service.owner.media_id
        if not media_id:
            return send_error_response(request, 400, "Something went wrong")

        old_images = service.images

        for img in old_images:
            if img.id not in schema.keep_image_ids:
                await delete_from_s3(img.image_url)
                await db.delete(img)

        images  = schema.images or []  
        for image in images:
            contents = await image.read()
            key      = f"media/{media_id}/services/{service.service_id}/images/{uuid.uuid4()}-{image.filename}"
            await upload_to_s3(contents, key, image.content_type)
            uploaded_keys.append(key)

            img = Image.open(io.BytesIO(contents))
            width, height = img.size
            db.add(ServiceImage(
                service_id=service.service_id,
                image_url=key,
                width=width, 
                height=height, 
                size=len(contents), 
                format=image.content_type or "",
            ))
        await db.flush()

        await db.refresh(service, attribute_names=["images"])

        return send_json_response(200, "Images updated", data=[
            {
                "image_id":  img.id,
                "image_url": _fmt_url(MEDIA_BASE_URL, img.image_url),
                "width":     img.width,
                "height":    img.height,
                "size":      img.size,
                "format":    img.format,
            }
            for img in service.images
        ])
    except Exception:
        for key in uploaded_keys:
            await delete_from_s3(key)
        return send_error_response(request, 500, "Internal server error")

async def update_service_plans(
    request:    Request,
    schema: UpdateServicePlansSchema,
    db:         AsyncSession,
):
    try:
        user_id = request.state.user.user_id
        service = await db.scalar(
            select(Service)
             .options(selectinload(Service.plans))
            .where(Service.service_id == schema.service_id, Service.created_by == user_id)
        )
        if not service:
            return send_error_response(request, 404, "Service not exist")

        plans_data = schema.plans
        existing_plans = service.plans
        existing_map = {p.id: p for p in service.plans}
        
        valid_ids = set()
        for plan in plans_data:
            plan_id       = plan.plan_id
            name          = plan.name
            description   = plan.description
            price         = plan.price
            price_unit    = plan.price_unit
            features      = json.dumps(plan.model_dump()["features"])
            delivery_time = plan.delivery_time
            duration_unit = plan.duration_unit

            existing = existing_map.get(plan_id)
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
                    service_id= schema.service_id,
                    name=name,
                    description=description,
                    price=price,
                    price_unit=price_unit,
                    features=features,
                    delivery_time=delivery_time,
                    duration_unit=duration_unit,
                )
                db.add(new_plan)
                await db.flush()
                valid_ids.add(new_plan.id)

        for old_plan in existing_plans:
            if old_plan.id not in valid_ids:
                await db.delete(old_plan)

        await db.flush()

        await db.refresh(service)
        return send_json_response(200, "Plans updated", data=_parse_plans(service.plans))
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def update_service_location(
    request:       Request,
    schema:       UpdateServiceLocationSchema,
    db:            AsyncSession,
):
    try:
        user_id = request.state.user.user_id
        service = await db.scalar(
            select(Service)
            .options(selectinload(Service.location))
            .where(Service.service_id == schema.service_id, Service.created_by == user_id)
        )
        if not service:
            return send_error_response(request, 404, "Service not found")

        loc = service.location
        if loc:
            loc.latitude      = schema.latitude
            loc.longitude     = schema.longitude
            loc.geo           = schema.geo
            loc.location_type = schema.location_type
            db.add(loc)
        else:
            db.add(ServiceLocation(
                service_id=schema.service_id,
                latitude=schema.latitude,
                longitude=schema.longitude,
                geo=schema.geo,
                location_type=schema.location_type,
            ))
        await db.flush()
        await db.refresh(service)

        return send_json_response(200, "Location updated", data={
            "latitude":      service.location.latitude,
            "longitude":     service.location.longitude,
            "geo":           service.location.geo,
            "location_type": service.location.location_type,
        })
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def delete_service(request: Request, schema: ServiceIdSchema, db: AsyncSession):
    try:
        user_id = request.state.user.user_id
        service = await db.scalar(
            select(Service).where(Service.service_id == schema.service_id, Service.created_by == user_id)
        )
        if not service:
            return send_error_response(request, 404, "Service not exist")

        media_id = await db.scalar(select(User.media_id).where(User.user_id == user_id))

        await db.delete(service)

        if media_id:
            await delete_directory_from_s3(f"media/{media_id}/services/{schema.service_id}")
        return send_json_response(200, "Service deleted")
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def bookmark_service(request: Request, schema:ServiceIdSchema, db: AsyncSession):
    try:
        user_id = request.state.user.user_id
        db.add(UserBookmarkService(user_id=user_id, service_id=schema.service_id))
        await db.flush()
        return send_json_response(200, "Bookmarked")
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def unbookmark_service(request: Request, schema:ServiceIdSchema, db: AsyncSession):
    try:
        user_id = request.state.user.user_id
        bookmark = await db.scalar(
            select(UserBookmarkService).where(
                UserBookmarkService.user_id == user_id,
                UserBookmarkService.service_id == schema.service_id,
            )
        )
        if not bookmark:
            return send_error_response(request, 404, "Faield to remove bookmark")
        await db.delete(bookmark)
        return send_json_response(200, "Unbookmarked")
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def services_search_suggestions(request: Request, schema: ServiceSearchSuggestionsSchema, db: AsyncSession):
    try:
        clean = schema.query.strip().lower()
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
        return send_json_response(200, "Suggestions fetched", data=[{"search_term": r.search_term} for r in result.scalars()])
    except Exception:
        return send_error_response(request, 500, "Internal server error")
    
async def get_industries(request: Request, db: AsyncSession):
    try:
        result = await db.execute(select(ServiceIndustry))
        industries = result.scalars().all()
        return send_json_response(200, "Service industries retrieved", data=[
            {"industry_id": i.industry_id, "name": i.industry_name, "description": i.description}
            for i in industries
        ])
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def get_user_industries(request: Request, db: AsyncSession):
    try:
        user_id = request.state.user.user_id
        user_service_industries = await db.execute(
            select(UserServiceIndustry.industry_id)
            .where(UserServiceIndustry.user_id == user_id)
        )
        selected_industries_ids = set(user_service_industries.scalars().all())

        result = await db.execute(select(ServiceIndustry))
        industries = result.scalars().all()

        return send_json_response(200, "Industries retrieved", data=[
            {
                "industry_id":   i.industry_id,
                "name": i.industry_name,
                "description":   i.description,
                "is_selected":   i.industry_id in selected_industries_ids  
            }
            for i in industries
        ])
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def update_industries(request: Request, schema: UpdateIndustriesSchema, db: AsyncSession):
    try:
        user_id = request.state.user.user_id
        industry_ids = schema.industries

        await db.execute(delete(UserServiceIndustry).where(UserServiceIndustry.user_id == user_id))
        await db.flush() 

        if industry_ids:
            stmt = insert(UserServiceIndustry).values(
                [{"user_id": user_id, "industry_id": ind_id} for ind_id in industry_ids]
            )
            stmt = stmt.on_duplicate_key_update(
                industry_id=stmt.inserted.industry_id
            )
            await db.execute(stmt)

        await db.flush()

        user_service_industries = await db.execute(
            select(UserServiceIndustry.industry_id)
            .where(UserServiceIndustry.user_id == user_id)
        )
        selected_industries_ids = set(user_service_industries.scalars().all())

        result = await db.execute(select(ServiceIndustry))
        industries = result.scalars().all()

        return send_json_response(200, "Industries updated", data=[
            {
                "industry_id":   i.industry_id,
                "name": i.industry_name,
                "description":   i.description,
                "is_selected":   i.industry_id in selected_industries_ids  
            }
            for i in industries
        ])
    except Exception as e:
        return send_error_response(request, 500, "Internal server error")
        