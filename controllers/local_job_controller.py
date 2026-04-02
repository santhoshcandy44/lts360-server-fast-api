import io
import json
import uuid
from datetime import datetime, timezone
from PIL import Image

from fastapi import Request

from kafka.notification_service_producer import send_local_job_applicant_applied_notification_to_kafka
from models.common import Country, State
from schemas.local_job_schemas import (
    MARITAL_STATUS_OPTIONS,
    CreateLocalJobSchema,
    GuestGetLocalJobsSchema,

    GetLocalJobsbSchema, 
    LocalJobIdSchema,
    
    GetPublishedLocalJobsSchema,
    GetLocalJobApplicationsSchema,
    LocalJobApplicationSchema,
    PublishLocalJobStateOptionsSchema,
    
    SearchSuggestionsSchema,
    UpdateLocalJobSchema
)

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from sqlalchemy import or_, and_, update, func, exists
from sqlalchemy.dialects.mysql import insert, match
from sqlalchemy.orm import selectinload

from models.local_job import LocalJobSearchQuery
from models.local_job import LocalJob, LocalJobImage, LocalJobLocation, LocalJobApplication, LocalJobSearchQuery
from models.user import User
from models.user import UserLocation
from models.bookmark import UserBookmarkLocalJob

from config import BASE_URL, PROFILE_BASE_URL, MEDIA_BASE_URL
from helpers.response_helper import send_json_response, send_error_response
from utils.pagination.cursor import encode_cursor, decode_cursor
from utils.aws_s3 import upload_to_s3, delete_from_s3, delete_directory_from_s3

SALARY_UNITS = [
    {"value": "INR", "name": "INR"},
    {"value": "USD", "name": "USD"},
]



def _fmt_url(base, path):
    return f"{base}/{path}" if path else ""

def _user_local_job_summary_response(
    local_job:          LocalJob,
    is_bookmarked: bool = False,
    is_applied:   bool = False,
    distance:     float | None = None,
) -> dict:
    SALARY_UNITS_MAP = {pu["value"]: pu for pu in SALARY_UNITS}
    return {
        "user": {
            "user_id":               local_job.owner.user_id,
            "first_name":            local_job.owner.first_name,
            "last_name":             local_job.owner.last_name,
            "is_verified":           bool(local_job.owner.is_email_verified),
            "profile_pic_url":       _fmt_url(PROFILE_BASE_URL, local_job.owner.profile_pic_url),
            "profile_pic_url_small": _fmt_url(PROFILE_BASE_URL, local_job.owner.profile_pic_url_96x96),
            "online":                bool(local_job.owner.chat_info.online) if local_job.owner.chat_info else False,
            "joined_at":             str(local_job.owner.created_at.year) if local_job.owner.created_at else None,
        },
        "local_job": {
            "local_job_id":    local_job.local_job_id,
            "title":           local_job.title,
            "description":     local_job.description,
            "salary_unit":     SALARY_UNITS_MAP[local_job.salary_unit],
            "salary_min":      local_job.salary_min,
            "salary_max":      local_job.salary_max,
            "slug":            f"{BASE_URL}/local-jobs/{local_job.short_code}",
            "is_bookmarked":   is_bookmarked,
            "is_applied":      is_applied,
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
                for img in sorted(local_job.images, key=lambda x: x.created_at, reverse=True)
            ],
            "location": {
                "geo":           local_job.location.geo,
            } if local_job.location else None,
        }
    }

def _local_job_detail_response(
    local_job:          LocalJob,
    is_bookmarked: bool = False,
    is_applied:   bool = False,
    distance:     float | None = None,
) -> dict:
    SALARY_UNITS_MAP = {pu["value"]: pu for pu in SALARY_UNITS}
    MARITAL_STATUS_MAP = {
        ms["value"]: ms for ms in MARITAL_STATUS_OPTIONS
    }
    statuses = json.loads(local_job.marital_statuses)

    return {
        "user": {
            "user_id":               local_job.owner.user_id,
            "first_name":            local_job.owner.first_name,
            "last_name":             local_job.owner.last_name,
            "is_verified":           bool(local_job.owner.is_email_verified),
            "profile_pic_url":       _fmt_url(PROFILE_BASE_URL, local_job.owner.profile_pic_url),
            "profile_pic_url_small": _fmt_url(PROFILE_BASE_URL, local_job.owner.profile_pic_url_96x96),
            "online":                bool(local_job.owner.chat_info.online) if local_job.owner.chat_info else False,
            "joined_at":             str(local_job.owner.created_at.year) if local_job.owner.created_at else None,
        },
        "local_job": {
            "local_job_id":    local_job.local_job_id,
            "title":           local_job.title,
            "description":     local_job.description,
            "company":         local_job.company,
            "age_min":         local_job.age_min,
            "age_max":         local_job.age_max,
            
            "marital_statuses": [
                MARITAL_STATUS_MAP[status] for status in statuses
            ],
            
            "salary_unit":     SALARY_UNITS_MAP[local_job.salary_unit],

            "salary_min":      local_job.salary_min,
            "salary_max":      local_job.salary_max,

            "country": {
                "country_id":   local_job.country.id,
                "name": local_job.country.name
            },

            "state": {
                "country_id":   local_job.state.country_id,
                "state_id":   local_job.state.id,
                "name": local_job.state.name
            },

            "slug":            f"{BASE_URL}/local-jobs/{local_job.short_code}",
            "is_bookmarked":   is_bookmarked,
            "is_applied":      is_applied,
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
                for img in sorted(local_job.images, key=lambda x: x.created_at, reverse=True)
            ],
            "location": {
                "geo":           local_job.location.geo,
            } if local_job.location else None,
        }
    }

def _published_local_job_response(
    local_job:          LocalJob,
) -> dict:
    SALARY_UNITS_MAP = {pu["value"]: pu for pu in SALARY_UNITS}
    MARITAL_STATUS_MAP = {
        ms["value"]: ms for ms in MARITAL_STATUS_OPTIONS
    }

    statuses = json.loads(local_job.marital_statuses)

    return {
            "local_job_id":    local_job.local_job_id,
            "title":           local_job.title,
            "description":     local_job.description,
            "company":         local_job.company,
            "age_min":         local_job.age_min,
            "age_max":         local_job.age_max,

           "marital_statuses": [
                MARITAL_STATUS_MAP[status] for status in statuses
            ],
            
            "salary_unit":     SALARY_UNITS_MAP[local_job.salary_unit],
            
            "salary_min":      local_job.salary_min,
            "salary_max":      local_job.salary_max,

            "country": {
                "country_id":   local_job.country.id,
                "name": local_job.country.name
            },

            "state": {
                "country_id":   local_job.state.country_id,
                "state_id":   local_job.state.id,
                "name": local_job.state.name
            },

            "status":          local_job.status,
            "slug":            f"{BASE_URL}/local-jobs/{local_job.short_code}",
            "images": [
                {
                    "image_id":  img.id,
                    "url": _fmt_url(MEDIA_BASE_URL, img.url),
                    "width":     img.width,
                    "height":    img.height,
                    "size":      img.size,
                    "format":    img.format,
                }
                for img in sorted(local_job.images, key=lambda x: x.created_at, reverse=True)
            ],
            "location": {
                "longitude":     float(local_job.location.longitude),
                "latitude":      float(local_job.location.latitude),
                "geo":           local_job.location.geo,
                "location_type": local_job.location.location_type,
            } if local_job.location else None,
    }

def _paginate_local_jobs(items: list, last_local_job:LocalJob | None, lastDistance: int | None, lastTotalRelavance: int | None,  page_size: int,  next_token: str = None ) -> dict:
    has_next       = len(items) == page_size and last_local_job is not None
    next_token_out = encode_cursor({
        "created_at":      str(last_local_job.created_at),
        "id":              last_local_job.id,
        "distance":        float(lastDistance) if lastDistance is not None else None,
        "total_relevance": float(lastTotalRelavance) if lastTotalRelavance is not None else None,
    }) if has_next else None
    return {
        "data":           items,
        "next_token":     next_token_out,
        "previous_token": next_token if next_token else None,
    }

def _paginate_jobs_by_job(items: list, last_local_job:LocalJob | None, page_size: int, next_token: str = None ) -> dict:
    has_next       = len(items) == page_size and last_local_job is not None
    next_token_out = encode_cursor({
        "created_at":      str(last_local_job.created_at),
        "id":              last_local_job.id
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
            func.cos(func.radians(LocalJobLocation.latitude)) *
            func.cos(func.radians(LocalJobLocation.longitude) - func.radians(lon)) +
            func.sin(func.radians(lat)) *
            func.sin(func.radians(LocalJobLocation.latitude))
        )
    ).label("distance")

def _relevance(query: str):
    return match(
        LocalJob.title,
        LocalJob.description,
        against=query
    ).label("total_relevance")

async def _query_local_jobs(
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
        stmt = insert(LocalJobSearchQuery).values(
            search_term=query,
            popularity=1,
            last_searched=datetime.now(timezone.utc),
            search_term_concatenated=query.replace(" ", ""),
        )
        stmt = stmt.on_duplicate_key_update(
            popularity=LocalJobSearchQuery.popularity + 1,
            last_searched=datetime.now(timezone.utc),
        )
        await db.execute(stmt)
    
    cols = [LocalJob]

    bookmark_subq = (
    exists()
    .where(
        UserBookmarkLocalJob.local_job_id == LocalJob.local_job_id,
        UserBookmarkLocalJob.user_id == user_id
    )).label("is_bookmarked")

    applicant_subq = (
    exists()
    .where(
        LocalJobApplication.local_job_id == LocalJob.local_job_id,
        LocalJobApplication.candidate_id == user_id
        )
    ).label("is_applied")

    if has_loc:
           distance_expr = _haversine(user_lat, user_lon)
           cols.append(distance_expr)
    if query:
            relevance_expr = _relevance(query)
            cols.append(relevance_expr)
    if user_id:
        cols.append(bookmark_subq)
        cols.append(applicant_subq)

    q = (
        select(*cols)
        .options(
            selectinload(LocalJob.images),    
            selectinload(LocalJob.location),
            selectinload(LocalJob.owner).selectinload(User.chat_info)
        )
    )

    if has_loc:
        q = q.join(
            LocalJobLocation,
            LocalJobLocation.local_job_id == LocalJob.local_job_id
        )

    if query:
        q = q.where(match(
            LocalJob.title,
            LocalJob.description,
            against=query,
        ) > 0)

    if payload:
        if has_loc and query:
                q = q.where(or_(
                    distance_expr > payload["distance"],
                    and_(distance_expr == payload["distance"], relevance_expr < payload["total_relevance"]),
                    and_(distance_expr == payload["distance"], relevance_expr == payload["total_relevance"], LocalJob.created_at < payload["created_at"]),
                    and_(distance_expr == payload["distance"], relevance_expr == payload["total_relevance"], LocalJob.created_at == payload["created_at"], LocalJob.id > payload["id"]),
                ))
        elif has_loc:
            q = q.where(or_(
                distance_expr > payload["distance"],
                and_(distance_expr == payload["distance"], LocalJob.created_at < payload["created_at"]),
                and_(distance_expr == payload["distance"], LocalJob.created_at == payload["created_at"], LocalJob.id > payload["id"]),
            ))
        elif query:
            q = q.where(or_(
                relevance_expr < payload["total_relevance"],
                and_(relevance_expr == payload["total_relevance"], LocalJob.created_at < payload["created_at"]),
                and_(relevance_expr == payload["total_relevance"], LocalJob.created_at == payload["created_at"], LocalJob.id > payload["id"]),
            ))
        else:
            q = q.where(or_(
                LocalJob.created_at < payload["created_at"],
                and_(LocalJob.created_at == payload["created_at"], LocalJob.id > payload["id"]),
            ))

    if has_loc and query:
        q = q.order_by(
            distance_expr.asc(),
            relevance_expr.desc(),
            LocalJob.created_at.desc(),
            LocalJob.id.asc()
        )
    elif has_loc:
        q = q.order_by(
            distance_expr.asc(),
            LocalJob.created_at.desc(),
            LocalJob.id.asc()
        )
    elif query:
        q = q.order_by(
            relevance_expr.desc(),
            LocalJob.created_at.desc(),
            LocalJob.id.asc()
        )
    else:
        q = q.order_by(
            LocalJob.created_at.desc(),
            LocalJob.id.asc()
        )

    q = q.limit(page_size)

    result = await db.execute(q)
    rows   = result.all()
    last_row  = None

    last_row = rows[-1] if rows else None

    localJobs = [
    _user_local_job_summary_response(
        row.LocalJob,
        bool(row.is_bookmarked) if user_id else False,
        bool(row.is_applied)    if user_id else False,
        float(row.distance)     if has_loc else None
    )
    for row in rows]
    
    return _paginate_local_jobs(
        localJobs,
        getattr(last_row, "LocalJob", None),
        getattr(last_row, "distance", None) if has_loc else None,
        getattr(last_row, "total_relevance", None) if query else None,
        page_size,
        next_token if payload else None,
    )

async def guest_get_local_jobs(request: Request, schema: GuestGetLocalJobsSchema, db: AsyncSession):
    try:
        s = schema.s
        page_size = 1
        next_token = schema.next_token
        
        lat = schema.latitude
        lon = schema.longitude

        data = await _query_local_jobs(db=db, page_size=page_size, query=s, user_lat=lat, user_lon=lon, next_token=next_token)

        return send_json_response(200, "Local jobs fetched", data= data)
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def get_local_jobs(request: Request, schema: GetLocalJobsbSchema, db: AsyncSession):
    try:
        user_id = request.state.user.user_id    

        s = schema.s
        page_size = 1
        next_token = schema.next_token

        loc = await db.scalar(select(UserLocation).where(UserLocation.user_id == user_id))
        lat, lon = (float(loc.latitude), float(loc.longitude)) if loc else (None, None)

        data = await _query_local_jobs(db=db, user_id=user_id, page_size=page_size, query=s, user_lat=lat, user_lon=lon, next_token=next_token)
        return send_json_response(200, "Local jobs fetched", data= data)
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def get_local_job(request: Request, schema: LocalJobIdSchema, db: AsyncSession):
    try:
        user_id = request.state.user.user_id
        local_job = await db.scalar(
            select(LocalJob)
            .options(
                selectinload(LocalJob.images),
                selectinload(LocalJob.location),
                selectinload(LocalJob.owner),
            )
            .where(LocalJob.local_job_id == schema.local_job_id)
        )

        if not local_job:
            return send_error_response(request, 404, "Local local_job not exist")
        
        is_applied = await db.scalar(
            select(LocalJobApplication)
            .where(LocalJobApplication.local_job_id == schema.local_job_id)
            .where(LocalJobApplication.candidate_id == str(user_id))
            ) is not None

        return send_json_response(200, "Local local_job retrived", data=_local_job_detail_response(
            local_job=local_job,
            is_applied=bool(is_applied),
        ))
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def apply_local_job(request: Request, schema: LocalJobIdSchema, db: AsyncSession):
    try:
        user_id = request.state.user.user_id
        local_job = await db.scalar(
            select(LocalJob).where(LocalJob.local_job_id == schema.local_job_id)
        )
        if not local_job:
            return send_error_response(request, 404, "Local local_job not exist")
        application = LocalJobApplication(
            candidate_id=user_id,
            local_job_id=schema.local_job_id
        )
        db.add(application)
        
        await db.flush()
        await db.refresh(application) 
        
        kafka_key = f"{local_job.created_by}:{schema.local_job_id}:{application.application_id}"
        await send_local_job_applicant_applied_notification_to_kafka(
            kafka_key = kafka_key,
            message={
                "user_id":          local_job.created_by,
                "candidate_id":     application.candidate_id,
                "application_id":   application.application_id,
                "title":  local_job.title,
            }
        )
        return send_json_response(200, "Applied successfully")
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def create_local_job(
    request: Request,
    schema:  CreateLocalJobSchema,
    db:      AsyncSession,
):
    images = schema.images or []
    uploaded_keys = []
    try:
        user_id  = request.state.user.user_id
        media_id = await db.scalar(select(User.media_id).where(User.user_id == user_id))
        if not media_id:
            return send_error_response(request, 400, "Something went wrong")

        country = await db.scalar(select(Country).where(Country.id == schema.country))
        if not country:
            return send_error_response(request, 400, "Invalid country")

        state = await db.scalar(
            select(State).where(State.id == schema.state, State.country_id == schema.country)
        )
        if not state:
            return send_error_response(request, 400, "Invalid state")

        new_local_job = LocalJob(
            title            = schema.title,
            description      = schema.description,
            company          = schema.company,
            age_min          = schema.age_min,
            age_max          = schema.age_max,
            salary_min       = schema.salary_min,
            salary_max       = schema.salary_max,
            salary_unit      = schema.salary_unit,
            marital_statuses = json.dumps(schema.marital_statuses),
            country_id       = country.id,
            state_id         = state.id,
            created_by       = user_id
        )
        db.add(new_local_job)
        await db.flush()

        for image in images:
            contents = await image.read()
            key = f"media/{media_id}/local-jobs/{new_local_job.local_job_id}/{uuid.uuid4()}-{image.filename}"
            await upload_to_s3(contents, key, image.content_type)
            uploaded_keys.append(key)

            img = Image.open(io.BytesIO(contents))
            width, height = img.size

            db.add(LocalJobImage(
                local_job_id = new_local_job.local_job_id,
                url          = key,
                width        = width,
                height       = height,
                size         = len(contents),
                format       = image.content_type or "",
            ))

        await db.flush()

        location = schema.location
        db.add(LocalJobLocation(
            local_job_id = new_local_job.local_job_id,
            latitude     = location["latitude"],
            longitude    = location["longitude"],
            geo          = location["geo"],
            location_type = location["location_type"],
        ))

        await db.flush()

        await db.refresh(new_local_job, attribute_names=["images", "location", "owner"])
        return send_json_response(200, "Local job published", data=_published_local_job_response(new_local_job))

    except Exception:
        await db.rollback()
        for key in uploaded_keys:
            await delete_from_s3(key)
        return send_error_response(request, 500, "Internal server error")


async def update_local_job(
    request:      Request,
    schema:       UpdateLocalJobSchema,
    db:           AsyncSession,
):
    images = schema.images or []
    uploaded_keys = []
    try:
        user_id  = request.state.user.user_id
        media_id = await db.scalar(select(User.media_id).where(User.user_id == user_id))
        if not media_id:
            return send_error_response(request, 400, "Something went wrong")

        existing = await db.scalar(
            select(LocalJob)
            .options(
                selectinload(LocalJob.images),
                selectinload(LocalJob.location),
                selectinload(LocalJob.owner),
            )
            .where(
                LocalJob.local_job_id == schema.local_job_id,
                LocalJob.created_by   == user_id,
            )
        )
        
        if not existing:
            return send_error_response(request, 404, "Local job not exist")
        
        media_id = existing.owner.media_id
        if not media_id:
            return send_error_response(request, 400, "Something went wrong")

        existing.title            = schema.title
        existing.description      = schema.description
        existing.company          = schema.company
        existing.age_min          = schema.age_min
        existing.age_max          = schema.age_max
        existing.salary_unit      = schema.salary_unit
        existing.salary_min       = schema.salary_min
        existing.salary_max       = schema.salary_max
        existing.marital_statuses = json.dumps(schema.marital_statuses)
        db.add(existing)

        await db.flush()

        keep_ids = set(schema.keep_image_ids or [])
        replace_ids = schema.replace_image_ids or []
        replace_images = schema.replace_images or []
        deleted_keys = []

        # delete images not in keep_ids and not in replace_ids
        for img in existing.images:
            if img.id not in keep_ids and img.id not in set(replace_ids):
                deleted_keys.append(img.url)
                await db.delete(img)

        # add new images
        for image in images:
            contents = await image.read()
            key = f"media/{media_id}/local-jobs/{existing.local_job_id}/{uuid.uuid4()}-{image.filename}"
            await upload_to_s3(contents, key, image.content_type)
            uploaded_keys.append(key)

            img = Image.open(io.BytesIO(contents))
            width, height = img.size

            db.add(LocalJobImage(
                local_job_id = existing.local_job_id,
                url          = key,
                width        = width,
                height       = height,
                size         = len(contents),
                format       = image.content_type or "",
            ))

        # replace existing images — zip ids with files
        for image_id, image in zip(replace_ids, replace_images):
            existing_img = next((img for img in existing.images if img.id == image_id), None)
            if not existing_img:
                continue

            contents = await image.read()
            new_key = f"media/{media_id}/local-jobs/{existing.local_job_id}/{uuid.uuid4()}-{image.filename}"
            await upload_to_s3(contents, new_key, image.content_type)
            uploaded_keys.append(new_key)

            old_key = existing_img.url
            deleted_keys.append(old_key)

            pil_img = Image.open(io.BytesIO(contents))
            width, height = pil_img.size

            existing_img.url    = new_key
            existing_img.width  = width
            existing_img.height = height
            existing_img.size   = len(contents)
            existing_img.format = image.content_type or ""
            db.add(existing_img)

        await db.flush()

        for key in deleted_keys:
            await delete_from_s3(key)

        await db.refresh(existing, attribute_names=["images", "location", "owner"])
        return send_json_response(200, "Local job updated", data=_published_local_job_response(existing))

    except Exception:
        await db.rollback()
        for key in uploaded_keys:
            await delete_from_s3(key)
        return send_error_response(request, 500, "Internal server error")

async def get_published_local_jobs(
    request: Request,
    schema: GetPublishedLocalJobsSchema,
    db: AsyncSession,
):
    try:
        user_id = request.state.user.user_id
        next_token = schema.next_token
        page_size = schema.page_size
        payload = decode_cursor(next_token) if next_token else None

        q = (
            select(LocalJob)
            .where(LocalJob.created_by == user_id)
            .options(
                selectinload(LocalJob.images),      
                selectinload(LocalJob.location),   
                selectinload(LocalJob.owner)      
            )
        )

        if payload:
            q = q.where(or_(
                LocalJob.created_at < payload["created_at"],
                and_(LocalJob.created_at == payload["created_at"], LocalJob.id > payload["id"]),
            ))

        q = q.order_by(LocalJob.created_at.desc(), LocalJob.id.asc()).limit(page_size)

        localJobs = (await db.execute(q)).scalars().all()

        items = [_published_local_job_response(local_job) for local_job in localJobs]
        last_row = localJobs[-1] if localJobs else None

        return send_json_response(
            200,
            "Local jobs retrieved",
            data=_paginate_jobs_by_job(items, getattr(last_row, "LocalJob", None), page_size, next_token if payload else None)
            )
    except Exception:
        import traceback
        import sys
        traceback.print_exc(file=sys.stderr)
        sys.stderr.flush()
        return send_error_response(request, 500, "Internal error")

async def get_published_local_job(
    request: Request,
    schema: LocalJobIdSchema,
    db: AsyncSession,
):
    try:
        user_id = request.state.user.user_id

        local_job = await db.scalar(
            select(LocalJob)
            .where(
                LocalJob.local_job_id == schema.local_job_id,
                LocalJob.created_by == user_id
            )
            .options(
                selectinload(LocalJob.images),
                selectinload(LocalJob.location),
                selectinload(LocalJob.owner)
            )
        )

        if not local_job:
            return send_error_response(request, 404, "Local job not found")

        return send_json_response(
            200,
            "Local job retrieved",
            data=_published_local_job_response(local_job)
        )
    except Exception:
        import traceback
        import sys
        traceback.print_exc(file=sys.stderr)
        sys.stderr.flush()
        return send_error_response(request, 500, "Internal server error")

async def delete_local_job(request: Request, schema: LocalJobIdSchema, db: AsyncSession):
    try:
        user_id = request.state.user.user_id
        local_job_id = schema.local_job_id

        local_job = await db.scalar(
            select(LocalJob).where(LocalJob.local_job_id == local_job_id, LocalJob.created_by == user_id)
        )
        if not local_job:
            return send_error_response(request, 404, "Local local_job not exist")

        media_id = await db.scalar(select(User.media_id).where(User.user_id == user_id))

        await db.delete(local_job)
        if media_id:
            await delete_directory_from_s3(f"media/{media_id}/local-localJobs/{local_job_id}")
 
        return send_json_response(200, "Loca job deleted")
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def get_local_job_applications(
    request: Request,
    schema: GetLocalJobApplicationsSchema,
    db: AsyncSession,
):
    local_job_id = schema.local_job_id,
    page_size = schema.page_size
    next_token =  schema.next_token

    payload   = decode_cursor(next_token) if next_token else None

    local_job = await db.scalar(select(LocalJob).where(LocalJob.local_job_id == local_job_id))
    if not local_job:
        return send_error_response(request, 404, "Local local_job not exist")

    q = (
        select(LocalJobApplication)
        .where(LocalJobApplication.local_job_id == local_job_id)
        .options(selectinload(LocalJobApplication.user))
    )

    if payload:
        q = q.where(or_(
            LocalJobApplication.is_reviewed > payload["is_reviewed"],
            and_(LocalJobApplication.is_reviewed == payload["is_reviewed"],
                 LocalJobApplication.reviewed_at < payload["reviewed_at"]),
            and_(LocalJobApplication.is_reviewed == payload["is_reviewed"],
                 LocalJobApplication.reviewed_at == payload["reviewed_at"],
                 LocalJobApplication.id > payload["id"]),
        ))

    q = q.order_by(
        LocalJobApplication.is_reviewed.asc(),
        LocalJobApplication.reviewed_at.desc(),
        LocalJobApplication.id.asc(),
    ).limit(page_size)

    rows = (await db.execute(q)).scalars().all()

    applications = []
    last_row = None

    for application in rows:
        u  = application.user
        ul = u.location if u else None

        applications.append({
            "application_id": application.application_id,
            "applied_at": str(application.applied_at.replace(tzinfo=timezone.utc).isoformat()) if application.applied_at else None,
            "is_reviewed": bool(application.is_reviewed),
            "contact_info": {
                "email": u.email,
                "phone_country_code": u.phone_country_code,
                "phone_number": u.phone_number,
            } if u else None,
            "user": {
                "user_id": u.user_id,
                "first_name": u.first_name,
                "last_name": u.last_name,
                "email": u.email,
                "is_email_verified": bool(u.is_email_verified),
                "phone_country_code": u.phone_country_code,
                "phone_number": u.phone_number,
                "is_phone_verified": bool(u.is_phone_verified),
                "profile_pic_url": _fmt_url(PROFILE_BASE_URL, u.profile_pic_url),
                "profile_pic_url_96x96": _fmt_url(PROFILE_BASE_URL, u.profile_pic_url_96x96),
                "geo": ul.geo if ul else None,
                "joined_at": str(u.created_at.year) if u.created_at else None,
            } if u else None,
        })
        last_row = application

    next_token_out = encode_cursor({
        "is_reviewed": last_row.is_reviewed,
        "reviewed_at": str(last_row.reviewed_at),
        "id": last_row.id,
    }) if len(applications) == page_size and last_row else None

    return send_json_response(200, "Applications fetched", data={
        "data": applications,
        "next_token": next_token_out,
        "previous_token": next_token if payload else None,
    })

async def mark_as_reviewed_local_job_application(request: Request, schema: LocalJobApplicationSchema, db: AsyncSession):
    try:
        user_id = request.state.user.user_id
        local_job = await db.scalar(
            select(LocalJob).where(LocalJob.local_job_id == schema.local_job_id, LocalJob.created_by == user_id)
        )
        if not local_job:
            return send_error_response(request, 404, "Local local_job not exist")

        await db.execute(
            update(LocalJobApplication)
            .where(LocalJobApplication.local_job_id == schema.local_job_id, LocalJobApplication.application_id == schema.application_id)
            .values(is_reviewed=1, reviewed_at=datetime.now(timezone.utc))
        )
        return send_json_response(200, "Marked as reviewed")
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def unmark_reviewed_local_job_application(request: Request, schema: LocalJobApplicationSchema, db: AsyncSession):
    try:
        user_id = request.state.user.user_id
        
        local_job = await db.scalar(
            select(LocalJob).where(LocalJob.local_job_id == schema.local_job_id, LocalJob.created_by == user_id)
        )
        if not local_job:
            return send_error_response(request, 404, "Local local_job not exist")

        await db.execute(
            update(LocalJobApplication)
            .where(LocalJobApplication.local_job_id == schema.local_job_id, LocalJobApplication.application_id == schema.application_id)
            .values(is_reviewed=0, reviewed_at=None)
        )
        return send_json_response(200, "Unmarked as reviewed")
    except Exception:
        return send_error_response(request, 500, "Internal server error")
    
async def bookmark_local_job(request: Request, schema:LocalJobIdSchema, db: AsyncSession):
    try:
        user_id = request.state.user.user_id
        db.add(UserBookmarkLocalJob(user_id=user_id, local_job_id=schema.local_job_id))
        return send_json_response(200, "Bookmarked")
    except Exception:
        return send_error_response(request, 500, "Internal server error")

async def unbookmark_local_job(request: Request, schema: LocalJobIdSchema, db: AsyncSession):
    try:
        user_id = request.state.user.user_id
        bookmark = await db.scalar(
            select(UserBookmarkLocalJob).where(
                UserBookmarkLocalJob.user_id == user_id,
                UserBookmarkLocalJob.local_job_id == schema.local_job_id,
            )
        )
        if not bookmark:
            return send_error_response(request, 404, "Failed to remove bookmark")
        await db.delete(bookmark)
        return send_json_response(200, "Bookmark removed")
    except Exception:
        return send_error_response(request, 500, "Internal server error")
    
async def local_jobs_search_suggestions(request: Request, schema: SearchSuggestionsSchema, db: AsyncSession):
    try:
        query = schema.query
        clean = query.strip().lower()
        words = clean.split()
        result = await db.execute(
            select(LocalJobSearchQuery)
            .where(or_(
                LocalJobSearchQuery.search_term.ilike(f"{clean}%"),
                *[LocalJobSearchQuery.search_term.ilike(f"%{w}%") for w in words],
                LocalJobSearchQuery.search_term_concatenated.ilike(f"{clean.replace(' ', '')}%"),
            ))
            .where(LocalJobSearchQuery.popularity > 1)
            .order_by(LocalJobSearchQuery.popularity.desc())
            .limit(10)
        )
        return send_json_response(200, "Suggestions retrieved", data=[{"search_term": r.search_term} for r in result.scalars()])
    except Exception:
        return send_error_response(request, 500, "Internal server error")
    


async def get_publish_meta_options(request: Request, db: AsyncSession):
    try:
        q = select(Country).order_by(Country.name)
        result = await db.execute(q)
        countries = result.scalars().all()
        return send_json_response(
            200,
            "Meta options fetched",
            data={
                "countries": [
                    {"country_id": c.id, "name": c.name}
                    for c in countries
                ],
                "marital_status_options": MARITAL_STATUS_OPTIONS,
                "salary_units": SALARY_UNITS
            }
        )
    except Exception:
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
    schema:  PublishLocalJobStateOptionsSchema,
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